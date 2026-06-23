"""
FastAPI backend for the Enterprise Data Agent.

Changes from the original app/api/server.py:
  - Switches from Workflow + single Runner to the new graph.run_graph() which
    fires explicit on_progress callbacks, giving reliable SSE phase events.
  - Adds GET / to serve the frontend HTML directly (no separate web server needed).
  - Properly extracts and returns chart_image_url in the result event.
  - Removes the _build_context_recap helper — context is now injected explicitly
    inside graph nodes rather than prepended to the top-level prompt.
  - Keeps all existing session/turn models and API surface unchanged.

Endpoints:
  GET  /                          - Serves frontend/index.html
  GET  /sessions                  - List all sessions
  POST /sessions                  - Create a new session
  GET  /sessions/{session_id}     - Get session history
  POST /sessions/{session_id}/ask - Stream SSE phase events + final result
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.config import initialize_mcp_connections
from app.orchestrator.graph import run_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("app.api.server")

# ---------------------------------------------------------------------------
# In-memory session store
# ---------------------------------------------------------------------------

class ChatTurn(BaseModel):
    question: str
    title: str | None = None
    document_url: str | None = None
    document_id: str | None = None
    chart_image_url: str | None = None
    error: str | None = None
    timestamp: str


class ChatSession(BaseModel):
    session_id: str
    created_at: str
    turns: list[ChatTurn] = []


sessions: dict[str, ChatSession] = {}
mcp_tools_map: dict[str, list] = {}
mcp_exit_stack = None

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_tools_map, mcp_exit_stack
    logger.info("Establishing MCP connections at startup...")
    mcp_tools_map, mcp_exit_stack = await initialize_mcp_connections()
    logger.info("MCP connections established. Backend ready.")
    yield
    logger.info("Shutting down MCP connections...")
    await mcp_exit_stack.aclose()
    logger.info("Shutdown complete.")


app = FastAPI(title="Enterprise Data Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

FRONTEND_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if not FRONTEND_PATH.exists():
        raise HTTPException(status_code=404, detail=f"Frontend not found at {FRONTEND_PATH}")
    return HTMLResponse(content=FRONTEND_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


@app.get("/sessions")
async def list_sessions():
    return [
        {"session_id": s.session_id, "title": s.turns[0].question[:60] if s.turns else "New analysis"}
        for s in sessions.values()
    ]


@app.post("/sessions")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = ChatSession(
        session_id=session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return {"session_id": session_id}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    s = sessions[session_id]
    return {
        "session_id": s.session_id,
        "turns": [t.model_dump() for t in s.turns],
    }


# ---------------------------------------------------------------------------
# Streaming ask endpoint
# ---------------------------------------------------------------------------

def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


@app.post("/sessions/{session_id}/ask")
async def ask(session_id: str, body: AskRequest):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    return StreamingResponse(
        _stream_graph(session_id, body.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_graph(session_id: str, question: str):
    """Runs the graph workflow, yielding SSE events to the client."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def on_progress(phase: str, status: str) -> None:
        await queue.put(_sse("phase", {"phase": phase, "status": status}))

    async def graph_task():
        try:
            result = await run_graph(
                user_query=question,
                bigquery_tools=mcp_tools_map.get("bigquery", []),
                charting_tools=mcp_tools_map.get("chart-generator", []),
                docs_tools=mcp_tools_map.get("google-docs", []),
                session_id=f"{session_id}_{uuid.uuid4().hex[:8]}",
                user_id=session_id,
                on_progress=on_progress,
            )

            # Persist turn
            turn = ChatTurn(
                question=question,
                title=result["title"],
                document_url=result["document_url"],
                document_id=result["document_id"],
                chart_image_url=result.get("chart_image_url"),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            sessions[session_id].turns.append(turn)

            await queue.put(_sse("result", {
                "question": question,
                "document_url": result["document_url"],
                "document_id": result["document_id"],
                "title": result["title"],
                "chart_image_url": result.get("chart_image_url"),
            }))

        except Exception as e:
            logger.exception(f"Graph execution error for session {session_id}: {e}")
            # Persist error turn
            sessions[session_id].turns.append(ChatTurn(
                question=question,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
            await queue.put(_sse("error", {"message": str(e)}))
        finally:
            await queue.put(None)  # sentinel

    task = asyncio.create_task(graph_task())

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item

    await task