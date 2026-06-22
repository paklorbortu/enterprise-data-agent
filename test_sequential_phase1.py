"""
Standalone test for the data_analyst_agent -> data_formatter_agent SequentialAgent pair.

Run with:
    uv run python test_sequential_phase1.py "your question here"

This validates that output_key/state templating correctly hands off data between
the two sub-agents before we build out the rest of the SequentialAgent pipeline.
Does not touch app/main.py or app/orchestrator/supervisor.py.
"""
import asyncio
import logging
import sys

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import initialize_mcp_connections
from app.agents.data_analyst import get_data_analyst_agent, get_data_formatter_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("test_sequential_phase1")

APP_NAME = "enterprise_data_agent_test"


async def main():
    question = " ".join(sys.argv[1:]).strip() or "What were total sales and profit by category in 2024?"

    print("====================================================================")
    print("Testing Phase 1 as a SequentialAgent (data_analyst -> data_formatter)")
    print(f"Question: {question}")
    print("====================================================================")

    tools_map, exit_stack = await initialize_mcp_connections()

    try:
        bigquery_tools = tools_map.get("bigquery", [])

        data_analyst_agent = get_data_analyst_agent(bigquery_tools)
        data_formatter_agent = get_data_formatter_agent()

        phase1_pipeline = SequentialAgent(
            name="phase1_data_pipeline",
            sub_agents=[data_analyst_agent, data_formatter_agent],
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
            agent=phase1_pipeline,
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

        # Fetch the final session state to inspect what output_key wrote
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        print("\n--------------------------------------------------------------------")
        print("Final session.state contents:")
        print("--------------------------------------------------------------------")
        for key, value in session.state.items():
            print(f"  {key}: {value}")

        print("\n--------------------------------------------------------------------")
        if "data_result" in session.state:
            print("SUCCESS: 'data_result' found in session state.")
            print(f"data_result = {session.state['data_result']}")
        else:
            print("FAILURE: 'data_result' NOT found in session state.")
        print("--------------------------------------------------------------------")

    finally:
        await exit_stack.aclose()


if __name__ == "__main__":
    asyncio.run(main())