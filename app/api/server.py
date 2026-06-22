"""
FastAPI backend for the Enterprise Data Agent.

Exposes:
  POST /sessions                  - create a new chat session
  GET  /sessions                  - list all sessions
  GET  /sessions/{session_id}     - get full history for a session
  POST /sessions/{session_id}/ask - ask a question, streams SSE progress + final result

MCP connections are established once at startup and reused across all requests.
Session/history storage is in-memory (resets on restart) — acceptable for this
capstone project; can be swapped for a persistent store later without changing
the API surface.
"""
import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import initialize_mcp_connections
from app.orchestrator.supervisor import build_pipeline
from app.agents import ReportGenerationResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("app.api.server")

ADK_APP_NAME = "enterprise_data_agent"

# --- In-memory state -------------------------------------------------------

class ChatTurn(BaseModel):
    question: str
    title: str | None = None
    document_url: str | None = None
    document_id: str | None = None
    chart_image_url: str | None = None
    data_summary: str | None = None
    error: str | None = None
    timestamp: str


class ChatSession(BaseModel):
    session_id: str
    created_at: str
    turns: list[ChatTurn] = []


sessions: dict[str, ChatSession] = {}
mcp_tools_map: dict[str, list] = {}
mcp_exit_stack = None


# --- Lifespan: connect MCP servers once at startup --------------------------

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


app = FastAPI(title="Enterprise Data Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before production use
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/response models -------------------------------------------------

class AskRequest(BaseModel):
    question: str


# --- Helpers -----------------------------------------------------------------

def _build_context_recap(session: ChatSession, new_question: str) -> str:
    """Builds a prompt that includes prior Q&A context for follow-up questions.

    Keeps context handling explicit and inspectable rather than relying on
    ADK's native session/conversation history, per design decision. Includes
    the actual data summary from prior turns (not just the report title), so
    the analyst agent has real numbers to reference for follow-ups like
    "now just show me Electronics" or "compare that to last quarter."
    """
    successful_turns = [t for t in session.turns if not t.error]
    if not successful_turns:
        return new_question

    lines = ["Previous conversation in this session:"]
    for turn in successful_turns:
        lines.append(f"Q: {turn.question}")
        if turn.data_summary:
            lines.append(f"A: Data found:\n{turn.data_summary}")
        else:
            lines.append("A: No data summary available.")
    lines.append(
        f"\nNew question: {new_question}\n"
        "If this question refers back to the previous data (e.g. 'that', 'it', "
        "a specific category/value mentioned above), use the previous data shown "
        "above as context, but still query BigQuery fresh to get accurate current data."
    )
    return "\n".join(lines)


# Map agent author names to human-readable phase labels for the frontend.
PHASE_LABELS = {
    "data_analyst_agent": "Querying BigQuery",
    "data_formatter_agent": "Structuring data",
    "charting_specialist_agent": "Generating chart",
    "charting_formatter_agent": "Finalizing chart data",
    "reporting_agent": "Writing report",
    "reporting_formatter_agent": "Finalizing report",
}


async def _run_pipeline_streaming(session: ChatSession, question: str):
    """Runs the pipeline for one question, yielding SSE-formatted strings as it goes."""
    full_prompt = _build_context_recap(session, question)

    pipeline = build_pipeline(
        bigquery_tools=mcp_tools_map.get("bigquery", []),
        charting_tools=mcp_tools_map.get("chart-generator", []),
        docs_tools=mcp_tools_map.get("google-docs", []),
    )

    session_service = InMemorySessionService()
    adk_session_id = f"{session.session_id}_{len(session.turns)}"
    await session_service.create_session(
        app_name=ADK_APP_NAME,
        user_id=session.session_id,
        session_id=adk_session_id,
    )

    runner = Runner(
        agent=pipeline,
        app_name=ADK_APP_NAME,
        session_service=session_service,
    )

    message = types.Content(parts=[types.Part(text=full_prompt)])

    last_phase_seen = None
    final_text_by_author: dict[str, str] = {}

    try:
        async for event in runner.run_async(
            user_id=session.session_id,
            session_id=adk_session_id,
            new_message=message,
        ):
            author = getattr(event, "author", None)

            text_preview = None
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        text_preview = part.text[:300]
                    if part.function_call:
                        logger.info(f"[DEBUG] author={author}, TOOL CALL: {part.function_call.name}({part.function_call.args})")
                    if part.function_response:
                        logger.info(f"[DEBUG] author={author}, TOOL RESPONSE: {str(part.function_response.response)[:500]}")
            logger.info(f"[DEBUG] author={author}, text_preview={text_preview!r}")

            if author and author != last_phase_seen and author in PHASE_LABELS:
                last_phase_seen = author
                yield _sse("phase", {"phase": author, "label": PHASE_LABELS[author], "status": "running"})

            if author and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    final_text_by_author[author] = text

        # Extract the structured results we need from the formatter agents' outputs
        data_raw = final_text_by_author.get("data_formatter_agent")
        chart_raw = final_text_by_author.get("charting_formatter_agent")
        report_raw = final_text_by_author.get("reporting_formatter_agent")

        if not report_raw:
            raise ValueError("Pipeline did not produce a final report.")

        report = ReportGenerationResult.model_validate_json(report_raw)

        chart_image_url = None
        if chart_raw:
            try:
                chart_data = json.loads(chart_raw)
                chart_image_url = chart_data.get("chart_image_url")
            except json.JSONDecodeError:
                pass

        data_summary = None
        if data_raw:
            try:
                data_summary = json.dumps(json.loads(data_raw))
            except json.JSONDecodeError:
                data_summary = data_raw

        turn = ChatTurn(
            question=question,
            title=report.title,
            document_url=report.document_url,
            document_id=report.document_id,
            chart_image_url=chart_image_url,
            data_summary=data_summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session.turns.append(turn)

        yield _sse("result", turn.model_dump())

    except Exception as e:
        logger.error(f"Pipeline error for session {session.session_id}: {e}")
        turn = ChatTurn(
            question=question,
            error=str(e),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session.turns.append(turn)
        yield _sse("error", {"message": str(e)})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# --- Routes --------------------------------------------------------------

@app.post("/sessions")
async def create_session():
    session_id = str(uuid.uuid4())
    session = ChatSession(
        session_id=session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    sessions[session_id] = session
    return {"session_id": session_id}


@app.get("/sessions")
async def list_sessions():
    return [
        {
            "session_id": s.session_id,
            "created_at": s.created_at,
            "title": s.turns[0].question if s.turns else "New conversation",
            "turn_count": len(s.turns),
        }
        for s in sorted(sessions.values(), key=lambda s: s.created_at, reverse=True)
    ]


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/sessions/{session_id}/ask")
async def ask(session_id: str, request: AskRequest):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        _run_pipeline_streaming(session, request.question),
        media_type="text/event-stream",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}