import os
import asyncio
from typing import List
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env (search upwards to project root)
load_dotenv(find_dotenv(usecwd=True))


async def _get_mcp_tools_via_adapter(server_configs: dict) -> List[object]:
    """Get MCP tools using the MultiServerMCPClient adapter with STDIO connections."""
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        print(f"[DEBUG] Creating MultiServerMCPClient with configs: {list(server_configs.keys())}")
    except ImportError as e:
        raise RuntimeError(
            "langchain-mcp-adapters is not installed. Please install it with: pip install langchain-mcp-adapters"
        ) from e

    try:
        # Create the multi-server MCP client with STDIO connections
        client = MultiServerMCPClient(server_configs)
        
        # Get all tools from all configured servers
        print(f"[DEBUG] Getting tools from MCP client...")
        tools = await client.get_tools()
        print(f"[DEBUG] Got {len(tools)} tools from MCP client")
        
        return tools
        
    except Exception as e:
        print(f"[DEBUG] Error in MCP adapter connection: {type(e).__name__}: {e}")
        import traceback
        print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
        raise


def _get_mcp_tools_sync(server_configs: dict) -> List[object]:
    """Synchronous wrapper for getting MCP tools."""
    async def _runner():
        return await _get_mcp_tools_via_adapter(server_configs)

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
    """Return all Firecrawl MCP tools using MultiServerMCPClient with STDIO.

    Environment variables used:
    - FIRECRAWL_API_KEY: API key for Firecrawl
    - FIRECRAWL_MCP_COMMAND: Command to start MCP server (default: npx)
    - FIRECRAWL_MCP_ARGS: Args for MCP server (default: -y firecrawl-mcp)
    """
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        print(f"[firecrawl mcp] FIRECRAWL_API_KEY not found, skipping MCP tools")
        return []
    
    # Get command and args for STDIO connection
    command = os.getenv("FIRECRAWL_MCP_COMMAND", "npx")
    args = os.getenv("FIRECRAWL_MCP_ARGS", "-y firecrawl-mcp").split()
    
    # Configure the Firecrawl MCP server for STDIO
    # Ensure environment variables are properly passed
    env_vars = {
        "FIRECRAWL_API_KEY": api_key,
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USERPROFILE": os.environ.get("USERPROFILE", ""),
        "TEMP": os.environ.get("TEMP", ""),
        "TMP": os.environ.get("TMP", "")
    }
    # Remove empty values
    env_vars = {k: v for k, v in env_vars.items() if v}
    
    server_config = {
        "firecrawl": {
            "transport": "stdio",
            "command": command,
            "args": args,
            "env": env_vars
        }
    }
    
    print(f"[firecrawl mcp] Connecting to Firecrawl MCP server via STDIO: {command} {' '.join(args)}")
    
    try:
        return _get_mcp_tools_sync(server_config)
    except Exception as e:
        print(f"[firecrawl mcp] Connection failed: {type(e).__name__}: {e}")
        print(f"[firecrawl mcp] Please ensure npx and firecrawl-mcp are available")
        print(f"[firecrawl mcp] Or start it manually: FIRECRAWL_API_KEY={api_key} npx -y firecrawl-mcp")
        return []


def get_microsoft_learn_mcp_tools() -> List[object]:
    """Return Microsoft Learn MCP tools using remote streamable HTTP connection.
    
    This connects to Microsoft's public MCP server that provides access to Learn content.
    No authentication required as per Microsoft Learn MCP Server documentation.
    
    More info: https://learn.microsoft.com/en-us/training/support/mcp
    """
    # Microsoft Learn MCP Server endpoint (no auth required)
    server_config = {
        "microsoft_learn": {
            "transport": "streamable_http",
            "url": "https://learn.microsoft.com/api/mcp"
        }
    }
    
    print(f"[microsoft learn mcp] Connecting to Microsoft Learn MCP server...")
    
    try:
        tools = _get_mcp_tools_sync(server_config)
        print(f"[microsoft learn mcp] Successfully connected! Got {len(tools)} tools")
        return tools
    except Exception as e:
        print(f"[microsoft learn mcp] Connection failed: {type(e).__name__}: {e}")
        print(f"[microsoft learn mcp] This is a remote server, check your internet connection")
        return []


def get_all_mcp_tools() -> List[object]:
    """Get all available MCP tools from Firecrawl, Microsoft Learn, and Unstructured servers."""
    all_tools = []
    
    # Get Firecrawl tools (web scraping)
    firecrawl_tools = get_firecrawl_mcp_tools()
    all_tools.extend(firecrawl_tools)
    
    # Get Microsoft Learn tools (documentation/markdown conversion)
    learn_tools = get_microsoft_learn_mcp_tools() 
    all_tools.extend(learn_tools)

    # Get Unstructured tools (document processing)
    unstructured_tools = get_unstructured_mcp_tools()
    all_tools.extend(unstructured_tools)
    
    print(
        f"[mcp] Total tools loaded: {len(all_tools)} (Firecrawl: {len(firecrawl_tools)}, Learn: {len(learn_tools)}, Unstructured: {len(unstructured_tools)})"
    )
    return all_tools


def _detect_python_interpreter_for_server() -> str:
    """Detect the Python interpreter to run the Unstructured MCP server.

    Prefer the project's root venv as per user rules; fall back to system python.
    """
    # If running inside an active venv, prefer that
    venv_dir = os.environ.get("VIRTUAL_ENV", "")
    candidates: list[str] = []
    if venv_dir:
        # Windows and POSIX
        candidates.append(os.path.join(venv_dir, "Scripts", "python.exe"))
        candidates.append(os.path.join(venv_dir, "bin", "python"))

    # Project-root .venv as per user convention
    project_root = os.getcwd()
    candidates.append(os.path.join(project_root, ".venv", "Scripts", "python.exe"))
    candidates.append(os.path.join(project_root, ".venv", "bin", "python"))

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return "python"


def get_unstructured_mcp_tools() -> List[object]:
    """Connect to Unstructured MCP server for document processing via STDIO.

    Environment variables used:
    - UNSTRUCTURED_API_KEY: Required. API key for Unstructured platform
    - UNSTRUCTURED_MCP_DIR: Required. Absolute path to `mcp-unstructured-server` directory
    - PATH/HOME/USERPROFILE/TEMP/TMP: Optional. Passed through for subprocess resolution
    - UNSTRUCTURED_OUTPUT_DIR: Optional. Output directory for processed files
    """
    api_key = os.getenv("UNSTRUCTURED_API_KEY", "")
    if not api_key:
        print("[unstructured_mcp] UNSTRUCTURED_API_KEY not found, skipping")
        return []

    mcp_server_dir = os.getenv("UNSTRUCTURED_MCP_DIR", "")
    if not mcp_server_dir:
        print("[unstructured_mcp] UNSTRUCTURED_MCP_DIR not found, skipping")
        return []

    # Determine interpreter (prefer root .venv)
    python_interp = _detect_python_interpreter_for_server()

    # Compose env for child process
    env_vars = {
        "UNSTRUCTURED_API_KEY": api_key,
        "UNSTRUCTURED_OUTPUT_DIR": os.getenv("UNSTRUCTURED_OUTPUT_DIR", ""),
        # Forward Supabase + Embeddings to the MCP server so it can persist & search
        "SUPABASE_URL": os.environ.get("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_ROLE_KEY": os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        "SUPABASE_ANON_KEY": os.environ.get("SUPABASE_ANON_KEY", ""),
        "SUPABASE_UPLOADS_BUCKET": os.environ.get("SUPABASE_UPLOADS_BUCKET", "context-uploads"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USERPROFILE": os.environ.get("USERPROFILE", ""),
        "TEMP": os.environ.get("TEMP", ""),
        "TMP": os.environ.get("TMP", ""),
    }
    env_vars = {k: v for k, v in env_vars.items() if v}

    # Run the server script by absolute path to avoid cwd issues
    server_entry = os.path.join(mcp_server_dir, "doc_processor.py")
    server_config = {
        "unstructured_partition": {
            "transport": "stdio",
            "command": python_interp,
            "args": [server_entry],
            "env": env_vars,
        }
    }

    print(
        f"[unstructured_mcp] Starting Unstructured MCP server using {python_interp} with entry {server_entry}"
    )

    try:
        tools = _get_mcp_tools_sync(server_config)
        print(f"[unstructured_mcp] Successfully connected! Got {len(tools)} tools")
        return tools
    except Exception as e:
        print(f"[unstructured_mcp] Failed to start: {type(e).__name__}: {e}")
        return []