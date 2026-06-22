"""
Standalone test for the FULL graph-based Workflow:
data_analyst -> data_formatter -> charting_specialist -> charting_formatter
-> reporting_agent -> reporting_formatter

reporting_agent needs BOTH the data_formatter's output (DataQueryResult) and
the charting_formatter's output (ChartingResult), not just the immediately
preceding node. This uses input_schema + the <ClassName.field from node_name>
instruction syntax to pull specific fields from named earlier nodes in the graph.

Run with:
    uv run python test_graph_full.py "your question here"
"""
import asyncio
import logging
import sys

from google.adk import Workflow
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import initialize_mcp_connections
from app.agents.data_analyst import get_data_analyst_agent, get_data_formatter_agent
from app.agents.charting_specialist import get_charting_specialist_agent, get_charting_formatter_agent
from app.agents.reporting import get_reporting_agent, get_reporting_formatter_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("test_graph_full")

APP_NAME = "enterprise_data_agent_test"


async def main():
    question = " ".join(sys.argv[1:]).strip() or "What were total sales and profit by category in 2024?"

    print("====================================================================")
    print("Testing FULL pipeline as a graph-based Workflow")
    print(f"Question: {question}")
    print("====================================================================")

    tools_map, exit_stack = await initialize_mcp_connections()

    try:
        bigquery_tools = tools_map.get("bigquery", [])
        charting_tools = tools_map.get("chart-generator", [])
        docs_tools = tools_map.get("google-docs", [])

        data_analyst_agent = get_data_analyst_agent(bigquery_tools)
        data_formatter_agent = get_data_formatter_agent()
        charting_specialist_agent = get_charting_specialist_agent(charting_tools)
        charting_formatter_agent = get_charting_formatter_agent()
        reporting_agent = get_reporting_agent(docs_tools)
        reporting_formatter_agent = get_reporting_formatter_agent()

        root_agent = Workflow(
            name="full_data_workflow",
            edges=[
                ("START", data_analyst_agent, data_formatter_agent,
                 charting_specialist_agent, charting_formatter_agent,
                 reporting_agent, reporting_formatter_agent),
            ],
        )

        session_service = InMemorySessionService()
        session_id = "test_session_1"
        user_id = "test_user"

        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        message = types.Content(parts=[types.Part(text=question)])

        events = [
            event async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message,
            )
        ]

        print(f"\nTotal events: {len(events)}")
        for i, event in enumerate(events):
            author = getattr(event, "author", "unknown")
            print(f"  Event {i}: author={author}")

        print("\n--------------------------------------------------------------------")
        print("Final event (should be the reporting formatter's structured output):")
        print("--------------------------------------------------------------------")
        if events:
            last_event = events[-1]
            if last_event.content and last_event.content.parts:
                print(last_event.content.parts[0].text)
        print("--------------------------------------------------------------------")

    finally:
        await exit_stack.aclose()


if __name__ == "__main__":
    asyncio.run(main())