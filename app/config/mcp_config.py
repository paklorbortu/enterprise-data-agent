import logging
from contextlib import AsyncExitStack
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from app.config.settings import MCP_SERVERS

logger = logging.getLogger("app.config.mcp_config")


async def initialize_mcp_connections() -> tuple[dict[str, list], AsyncExitStack]:
    """Connects to configured MCP servers. Failures are logged but non-fatal —
    a server that fails to connect returns an empty tools list so the FastAPI
    server can still start and serve requests for working servers."""
    exit_stack = AsyncExitStack()
    tools_map: dict[str, list] = {}

    logger.info("Initializing MCP server connections...")

    for server_name, server_config in MCP_SERVERS.items():
        try:
            logger.info(f"Connecting to MCP server: {server_name}")
            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env"),
                cwd=server_config.get("cwd"),
            )
            connection_params = StdioConnectionParams(
                server_params=server_params,
                timeout=server_config.get("timeout", 60),
            )
            toolset = McpToolset(connection_params=connection_params)
            exit_stack.push_async_callback(toolset.close)
            tools = await toolset.get_tools()
            logger.info(f"Connected to {server_name}: {len(tools)} tools available.")
            tools_map[server_name] = tools

        except Exception as e:
            logger.error(f"MCP server '{server_name}' failed to connect: {e}")
            # Unwrap nested ExceptionGroup for easier debugging
            def _unwrap(exc, depth=0):
                logger.error(f"[DEBUG] {'  ' * depth}{type(exc).__name__}: {exc}")
                if hasattr(exc, "exceptions"):
                    for sub in exc.exceptions:
                        _unwrap(sub, depth + 1)
                if exc.__cause__:
                    _unwrap(exc.__cause__, depth + 1)
            _unwrap(e)
            tools_map[server_name] = []

    connected = [k for k, v in tools_map.items() if v]
    failed = [k for k, v in tools_map.items() if not v]
    logger.info(f"MCP init complete. Connected: {connected}. Failed/empty: {failed}")

    return tools_map, exit_stack