import os
import shlex
import asyncio
from typing import List


def _split_args(args_string: str) -> list[str]:
    if not args_string:
        return []
    return shlex.split(args_string)


async def _connect_mcp_server(command: str, args: list[str], env: dict | None):
    try:
        from langchain_mcp import MCPToolkit
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "langchain_mcp is not installed. Please install it (e.g., `pip install langchain-mcp`)."
        ) from e

    toolkit = await MCPToolkit.from_server(command=command, args=args, env=env)
    return toolkit


def _get_mcp_tools(command: str, args: list[str], env: dict | None) -> List[object]:
    async def _runner():
        toolkit = await _connect_mcp_server(command=command, args=args, env=env)
        # Prefer get_tools() if available; fall back to .tools
        if hasattr(toolkit, "get_tools"):
            return toolkit.get_tools()
        return getattr(toolkit, "tools", [])

    try:
        return asyncio.run(_runner())
    except RuntimeError as e:
        # If already in an event loop (e.g., Jupyter), provide a helpful error
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            raise RuntimeError(
                "Attempted to load MCP tools inside a running event loop. "
                "Please call these helpers at program startup, or adapt to use awaitable variants."
            ) from e
        raise


def get_firecrawl_mcp_tools() -> List[object]:
    """Return all Firecrawl MCP tools as LangChain tools.

    Environment variables used:
    - FIRECRAWL_API_KEY: API key for Firecrawl (forwarded to server)
    - FIRECRAWL_MCP_COMMAND: Command to start the MCP server (default: "npx")
    - FIRECRAWL_MCP_ARGS: Arguments for the MCP server command. Default attempts to use
      the official package name.
    """
    command = os.getenv("FIRECRAWL_MCP_COMMAND", "npx")
    default_args = "-y @modelcontextprotocol/server-firecrawl"
    args = _split_args(os.getenv("FIRECRAWL_MCP_ARGS", default_args))

    env = {
        # Forward only needed env vars to the MCP server process
        "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", ""),
    }
    # Merge with current environment minimally to preserve PATH, etc.
    merged_env = {**os.environ, **env}

    try:
        return _get_mcp_tools(command=command, args=args, env=merged_env)
    except Exception as e:  # noqa: BLE001
        # Gracefully degrade: if MCP server isn't available, return empty tool list
        print(f"[firecrawl mcp] Failed to load MCP tools: {e}")
        return []


def get_replicate_mcp_tools() -> List[object]:
    """Return all Replicate MCP tools as LangChain tools.

    Environment variables used:
    - REPLICATE_API_TOKEN: API token for Replicate (forwarded to server)
    - REPLICATE_MCP_COMMAND: Command to start the MCP server (default: "npx")
    - REPLICATE_MCP_ARGS: Arguments for the MCP server command. Default attempts to use
      the official package name.
    """
    command = os.getenv("REPLICATE_MCP_COMMAND", "npx")
    default_args = "-y @modelcontextprotocol/server-replicate"
    args = _split_args(os.getenv("REPLICATE_MCP_ARGS", default_args))

    env = {
        # Forward only needed env vars to the MCP server process
        "REPLICATE_API_TOKEN": os.getenv("REPLICATE_API_TOKEN", ""),
    }
    merged_env = {**os.environ, **env}

    try:
        return _get_mcp_tools(command=command, args=args, env=merged_env)
    except Exception as e:  # noqa: BLE001
        print(f"[replicate mcp] Failed to load MCP tools: {e}")
        return []