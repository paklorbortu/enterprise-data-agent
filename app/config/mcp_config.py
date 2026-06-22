import logging
from contextlib import AsyncExitStack
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from app.config.settings import MCP_SERVERS

logger = logging.getLogger("app.config.mcp_config")

async def initialize_mcp_connections() -> tuple[dict[str, list], AsyncExitStack]:
    """Dynamically connects to configured MCP servers via standard stdio transport.
    
    Loops through MCP_SERVERS in app/config/settings.py to initialize StdioServerParameters
    and McpToolset connections. Registers close callbacks on an AsyncExitStack to prevent
    zombie subprocess/resource leaks on connection failures.
    
    Returns:
        A tuple of (tools_map, exit_stack_instance).
    
    Raises:
        ConnectionError: If any MCP server fails to connect.
    """
    exit_stack = AsyncExitStack()
    tools_map = {}
    
    logger.info("Initializing Model Context Protocol (MCP) server connections...")
    
    try:
        for server_name, server_config in MCP_SERVERS.items():
            logger.info(f"Connecting to MCP server: {server_name}")
            
            # Map configuration parameters to StdioServerParameters, then wrap in
            # StdioConnectionParams so we can configure a generous timeout. Plain
            # StdioServerParameters does not support timeout and silently enforces
            # ADK's hardcoded 5-second default, which is too short for cross-region
            # BigQuery calls (this dataset lives in asia-east1).
            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env"),
                cwd=server_config.get("cwd")
            )
            connection_params = StdioConnectionParams(
                server_params=server_params,
                timeout=server_config.get("timeout", 60),
            )
            
            # Create the McpToolset instance
            toolset = McpToolset(connection_params=connection_params)
            
            # Register connection cleanup with the exit stack immediately
            exit_stack.push_async_callback(toolset.close)
            
            # Call get_tools() to trigger the connection and retrieve discovered tools
            tools = await toolset.get_tools()
            logger.info(f"Successfully connected to {server_name}. Discovered {len(tools)} tools.")
            tools_map[server_name] = tools
            
        return tools_map, exit_stack
        
    except Exception as e:
        logger.error(
            f"Failed to connect to MCP server: {server_name}. "
            f"Error: {e}. Cleaning up connections to prevent resource leaks."
        )
        # Unwrap ExceptionGroup/BaseExceptionGroup to see the real nested error,
        # since ADK's MCP session manager wraps everything in a generic TaskGroup error.
        def _unwrap(exc, depth=0):
            logger.error(f"[DEBUG] {'  ' * depth}{type(exc).__name__}: {exc}")
            if hasattr(exc, "exceptions"):
                for sub_exc in exc.exceptions:
                    _unwrap(sub_exc, depth + 1)
            if exc.__cause__:
                logger.error(f"[DEBUG] {'  ' * depth}Caused by:")
                _unwrap(exc.__cause__, depth + 1)
        _unwrap(e)

        # Safely clean up any successfully opened connections
        await exit_stack.aclose()
        raise ConnectionError(f"MCP client initialization failed on {server_name}: {e}") from e
