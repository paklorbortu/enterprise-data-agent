"""
Standalone test for the data_analyst_agent -> data_formatter_agent pair using
ADK 2.0's graph-based Workflow (edges syntax), as a replacement for the
deprecated SequentialAgent.

Run with:
    uv run python test_graph_phase1.py "your question here"
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("test_graph_phase1")

APP_NAME = "enterprise_data_agent_test"


async def main():
    question = " ".join(sys.argv[1:]).strip() or "What were total sales and profit by category in 2024?"

    print("====================================================================")
    print("Testing Phase 1 as a graph-based Workflow (data_analyst -> data_formatter)")
    print(f"Question: {question}")
    print("====================================================================")

    tools_map, exit_stack = await initialize_mcp_connections()

    try:
        bigquery_tools = tools_map.get("bigquery", [])

        data_analyst_agent = get_data_analyst_agent(bigquery_tools)
        data_formatter_agent = get_data_formatter_agent()

        root_agent = Workflow(
            name="phase1_data_workflow",
            edges=[
                ("START", data_analyst_agent, data_formatter_agent),
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
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"    text: {part.text[:300]}")

        print("\n--------------------------------------------------------------------")
        print("Final event (should be the formatter's structured output):")
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