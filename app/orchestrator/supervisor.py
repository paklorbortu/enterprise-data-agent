import logging
from google.adk import Workflow
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agents import (
    get_data_analyst_agent,
    get_data_formatter_agent,
    get_charting_specialist_agent,
    get_charting_formatter_agent,
    get_reporting_agent,
    get_reporting_formatter_agent,
    ReportGenerationResult,
)

logger = logging.getLogger("app.orchestrator.supervisor")

APP_NAME = "enterprise_data_agent"


def build_pipeline(bigquery_tools: list, charting_tools: list, docs_tools: list) -> Workflow:
    """Builds the full six-agent graph-based Workflow pipeline.

    Data flow:
      data_analyst -> data_formatter -> charting_specialist -> charting_formatter
      -> reporting_agent -> reporting_formatter

    data_formatter writes its DataQueryResult JSON to session state via
    output_key="data_result". charting_formatter writes its ChartingResult JSON
    via output_key="chart_result". reporting_agent's instruction references both
    via {data_result} and {chart_result} templating — the correct ADK pattern for
    accessing non-adjacent nodes' outputs, replacing the broken cross-node
    <ClassName.field from node_name> syntax.

    reporting_agent has no mode="single_turn" because it needs multiple
    tool-calling round-trips to create and populate the Google Doc.
    """
    data_analyst_agent = get_data_analyst_agent(bigquery_tools)

    data_formatter_agent = get_data_formatter_agent()
    data_formatter_agent.output_key = "data_result"

    charting_specialist_agent = get_charting_specialist_agent(charting_tools)

    charting_formatter_agent = get_charting_formatter_agent()
    charting_formatter_agent.output_key = "chart_result"

    reporting_agent = get_reporting_agent(docs_tools)
    reporting_formatter_agent = get_reporting_formatter_agent()

    return Workflow(
        name="enterprise_data_pipeline",
        edges=[
            ("START", data_analyst_agent, data_formatter_agent,
             charting_specialist_agent, charting_formatter_agent,
             reporting_agent, reporting_formatter_agent),
        ],
    )


async def run_orchestrated_flow(
    user_query: str,
    bigquery_tools: list,
    charting_tools: list,
    docs_tools: list,
    session_id: str = "orchestrator_session",
    user_id: str = "default_user",
) -> dict:
    """Runs the full pipeline for a single question and returns the final report metadata."""
    logger.info(f"Starting orchestration flow for query: '{user_query}'")

    pipeline = build_pipeline(bigquery_tools, charting_tools, docs_tools)

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        agent=pipeline,
        app_name=APP_NAME,
        session_service=session_service,
    )

    message = types.Content(parts=[types.Part(text=user_query)])

    all_events = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        author = getattr(event, "author", "unknown")
        text_preview = None
        if event.content and event.content.parts and event.content.parts[0].text:
            text_preview = event.content.parts[0].text[:200]
        logger.info(f"[DEBUG] Event: author={author}, text_preview={text_preview!r}")
        all_events.append(event)

    # Walk backward to find the reporting_formatter_agent's structured output.
    # Blindly trusting the last event is unreliable — ADK may emit trailing
    # non-text events after the formatter's real response.
    raw_text = None
    for event in reversed(all_events):
        author = getattr(event, "author", None)
        if author == "reporting_formatter_agent" and event.content and event.content.parts:
            candidate = event.content.parts[0].text
            if candidate:
                raw_text = candidate
                break

    if not raw_text:
        raise ValueError(
            f"Pipeline did not produce a final structured response from "
            f"reporting_formatter_agent. Total events: {len(all_events)}."
        )

    report = ReportGenerationResult.model_validate_json(raw_text)
    logger.info("Orchestration flow complete. Report created successfully.")

    return {
        "document_url": report.document_url,
        "document_id": report.document_id,
        "title": report.title,
    }