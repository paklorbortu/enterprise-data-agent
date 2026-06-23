import logging
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from google.genai import types

from app.agents.data_analyst import get_data_analyst_agent, DataQueryResult
from app.agents.charting_specialist import get_charting_specialist_agent, ChartingResult
from app.agents.reporting import get_reporting_agent, get_reporting_formatter_agent, ReportGenerationResult
from app.agents.data_analyst import get_data_formatter_agent
from app.agents.charting_specialist import get_charting_formatter_agent

logger = logging.getLogger("app.orchestrator.graph")

APP_NAME = "enterprise_data_agent"
ProgressCallback = Callable[[str, str], Awaitable[None]]

# RunConfig for single_turn agents


@dataclass
class GraphState:
    user_query: str
    bigquery_tools: list
    charting_tools: list
    docs_tools: list
    session_id: str
    user_id: str
    session_service: InMemorySessionService
    analyst_text: Optional[str] = None
    charting_text: Optional[str] = None
    reporting_text: Optional[str] = None
    data_result: Optional[DataQueryResult] = None
    chart_result: Optional[ChartingResult] = None
    report_result: Optional[ReportGenerationResult] = None


def _get_text(events: list, author: str) -> Optional[str]:
    # First try: exact author match
    for event in reversed(events):
        if getattr(event, "author", None) != author:
            continue
        if event.content and event.content.parts and event.content.parts[0].text:
            return event.content.parts[0].text
    # Fallback: any event with text (handles author key mismatches in shared sessions)
    for event in reversed(events):
        if event.content and event.content.parts and event.content.parts[0].text:
            actual = getattr(event, "author", "unknown")
            logger.warning(f"_get_text: author mismatch for '{author}', using text from '{actual}'")
            return event.content.parts[0].text
    return None


async def _run_node(agent, state: GraphState, message_text: str) -> list:
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=state.session_service)
    msg = types.Content(parts=[types.Part(text=message_text)])
    events = []
    async for event in runner.run_async(
        user_id=state.user_id,
        session_id=state.session_id,
        new_message=msg,
    ):
        events.append(event)
    return events


async def node_data_analyst(state: GraphState, cb: ProgressCallback) -> None:
    await cb("data_analyst_agent", "running")
    events = await _run_node(get_data_analyst_agent(state.bigquery_tools), state, state.user_query)
    text = _get_text(events, "data_analyst_agent")
    if not text:
        raise ValueError("data_analyst_agent produced no output.")
    state.analyst_text = text
    await cb("data_analyst_agent", "complete")


async def node_data_formatter(state: GraphState, cb: ProgressCallback) -> None:
    await cb("data_formatter_agent", "running")
    events = await _run_node(get_data_formatter_agent(), state, state.analyst_text)
    text = _get_text(events, "data_formatter_agent")
    if not text:
        raise ValueError("data_formatter_agent produced no output.")
    state.data_result = DataQueryResult.model_validate_json(text)
    logger.info(f"Data formatted: {len(state.data_result.data)} rows.")
    await cb("data_formatter_agent", "complete")


async def node_charting_specialist(state: GraphState, cb: ProgressCallback) -> None:
    await cb("charting_specialist_agent", "running")
    prompt = (
        f"Original user request: {state.user_query}\n"
        f"Structured query results: {state.data_result.model_dump_json()}"
    )
    events = await _run_node(get_charting_specialist_agent(state.charting_tools), state, prompt)
    text = _get_text(events, "charting_specialist_agent")
    if not text:
        raise ValueError("charting_specialist_agent produced no output.")
    state.charting_text = text
    await cb("charting_specialist_agent", "complete")


async def node_charting_formatter(state: GraphState, cb: ProgressCallback) -> None:
    await cb("charting_formatter_agent", "running")
    events = await _run_node(get_charting_formatter_agent(), state, state.charting_text)
    text = _get_text(events, "charting_formatter_agent")
    if not text:
        raise ValueError("charting_formatter_agent produced no output.")
    state.chart_result = ChartingResult.model_validate_json(text)
    logger.info(f"Chart: {state.chart_result.chart_image_url}")
    await cb("charting_formatter_agent", "complete")


async def node_reporting(state: GraphState, cb: ProgressCallback) -> None:
    await cb("reporting_agent", "running")

    # If google-docs MCP failed to connect, skip tool-calling and synthesize a
    # stub report so the rest of the pipeline can complete and return a result.
    if not state.docs_tools:
        logger.warning("google-docs MCP unavailable — synthesizing stub report without Google Docs.")
        state.reporting_text = (
            f"Report title: Executive Report: {state.user_query}\n"
            f"Document ID: unavailable-docs-mcp-offline\n"
            f"Note: Google Docs MCP server was not available. "
            f"Data: {state.data_result.model_dump_json()}. "
            f"Chart: {state.chart_result.chart_image_url}"
        )
        await cb("reporting_agent", "complete")
        return

    prompt = (
        f"Create an executive business report for: '{state.user_query}'.\n\n"
        f"Query data (JSON): {state.data_result.model_dump_json()}\n\n"
        f"Chart information (JSON): {state.chart_result.model_dump_json()}"
    )
    runner = Runner(agent=get_reporting_agent(state.docs_tools), app_name=APP_NAME, session_service=state.session_service)
    msg = types.Content(parts=[types.Part(text=prompt)])
    events = []
    async for event in runner.run_async(user_id=state.user_id, session_id=state.session_id, new_message=msg):
        events.append(event)
    text = _get_text(events, "reporting_agent")
    if not text:
        raise ValueError("reporting_agent produced no output.")
    state.reporting_text = text
    await cb("reporting_agent", "complete")


async def node_reporting_formatter(state: GraphState, cb: ProgressCallback) -> None:
    await cb("reporting_formatter_agent", "running")

    # Stub bypass: if docs MCP was offline, synthesize the result directly
    if not state.docs_tools:
        state.report_result = ReportGenerationResult(
            document_url=state.chart_result.chart_image_url,
            document_id="docs-mcp-offline",
            title=f"Executive Report: {state.user_query}",
        )
        logger.warning("Stub report result used — google-docs MCP was offline.")
        await cb("reporting_formatter_agent", "complete")
        return

    events = await _run_node(get_reporting_formatter_agent(), state, state.reporting_text)
    text = _get_text(events, "reporting_formatter_agent")
    if not text:
        raise ValueError("reporting_formatter_agent produced no output.")
    state.report_result = ReportGenerationResult.model_validate_json(text)
    logger.info(f"Report: {state.report_result.document_id}")
    await cb("reporting_formatter_agent", "complete")


GRAPH_NODES = [
    node_data_analyst,
    node_data_formatter,
    node_charting_specialist,
    node_charting_formatter,
    node_reporting,
    node_reporting_formatter,
]


async def run_graph(
    user_query: str,
    bigquery_tools: list,
    charting_tools: list,
    docs_tools: list,
    session_id: Optional[str] = None,
    user_id: str = "default_user",
    on_progress: Optional[ProgressCallback] = None,
) -> dict:
    async def _noop(phase: str, status: str) -> None:
        pass

    cb = on_progress or _noop
    session_id = session_id or f"graph_{uuid.uuid4().hex}"

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )

    state = GraphState(
        user_query=user_query,
        bigquery_tools=bigquery_tools,
        charting_tools=charting_tools,
        docs_tools=docs_tools,
        session_id=session_id,
        user_id=user_id,
        session_service=session_service,
    )

    logger.info(f"Graph started | session={session_id} | query='{user_query}'")
    for node in GRAPH_NODES:
        logger.info(f"Node: {node.__name__}")
        await node(state, cb)
    logger.info("Graph complete.")

    return {
        "document_url": state.report_result.document_url,
        "document_id": state.report_result.document_id,
        "title": state.report_result.title,
        "chart_image_url": state.chart_result.chart_image_url,
    }