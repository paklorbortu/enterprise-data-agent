import asyncio
import logging
import sys
from app.config import initialize_mcp_connections
from app.orchestrator.supervisor import run_orchestrated_flow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("app.main")

async def main():
    print("====================================================================")
    print("Initializing ADK 2.0 Multi-Agent Enterprise System...")
    print("====================================================================")

    try:
        tools_map, exit_stack = await initialize_mcp_connections()
    except Exception as e:
        logger.error(f"Failed to establish MCP client connections: {e}")
        return

    try:
        bigquery_tools = tools_map.get("bigquery", [])
        charting_tools = tools_map.get("chart-generator", [])
        docs_tools = tools_map.get("google-docs", [])

        cli_args = sys.argv[1:]
        initial_prompt = " ".join(cli_args).strip() if cli_args else None
        session_counter = 0

        while True:
            if initial_prompt:
                target_prompt = initial_prompt
                initial_prompt = None
            else:
                print("\n--------------------------------------------------------------------")
                target_prompt = input("Ask a question about the sales data (or 'exit' to quit): ").strip()
                if target_prompt.lower() in ("exit", "quit", ""):
                    break

            session_counter += 1
            session_id = f"orchestrator_session_{session_counter}"

            print("\n--------------------------------------------------------------------")
            print(f"Triggering Orchestration Flow")
            print(f"Prompt: '{target_prompt}'")
            print("--------------------------------------------------------------------")

            try:
                result = await run_orchestrated_flow(
                    user_query=target_prompt,
                    bigquery_tools=bigquery_tools,
                    charting_tools=charting_tools,
                    docs_tools=docs_tools,
                    session_id=session_id,
                )

                print("\n====================================================================")
                print("ORCHESTRATION COMPLETED SUCCESSFULLY")
                print("====================================================================")
                print(f"Report Title: {result.get('title')}")
                print(f"Document ID:  {result.get('document_id')}")
                print(f"Google Doc:   {result.get('document_url')}")
                print("====================================================================\n")

            except Exception as e:
                print("\n====================================================================")
                logger.error(f"An error occurred during multi-agent orchestration execution: {e}")
                print("====================================================================\n")

            if not sys.stdin.isatty():
                break
            if len(cli_args) > 0 and session_counter == 1:
                break

    finally:
        print("Terminating background MCP Node subprocess channels safely...")
        await exit_stack.aclose()
        print("Cleanup completed. System shutdown.")

if __name__ == "__main__":
    asyncio.run(main())