# MCP Integration Guide

This guide shows how to add MCP (Model Context Protocol) tools to the Deep Agents framework based on proven, working implementations.

## Quick Start

The project comes with **Firecrawl** and **Microsoft Learn** MCP integrations that work out of the box:

```python
from deepagents.mcp_tools import get_all_mcp_tools

# Get all MCP tools (recommended)
mcp_tools = get_all_mcp_tools()

# Or get individual tool sets
from deepagents.mcp_tools import get_firecrawl_mcp_tools, get_microsoft_learn_mcp_tools
firecrawl_tools = get_firecrawl_mcp_tools()  # Web scraping
learn_tools = get_microsoft_learn_mcp_tools()  # Microsoft docs
```

## Environment Setup

### 1. Install Dependencies
```bash
pip install langchain-mcp-adapters
```

### 2. Configure Environment Variables
Add to your `.env` file:
```bash
# Firecrawl MCP (for web scraping)
FIRECRAWL_API_KEY=your-firecrawl-api-key
FIRECRAWL_MCP_COMMAND=npx
FIRECRAWL_MCP_ARGS=-y firecrawl-mcp

# Microsoft Learn MCP requires no configuration (public server)
```

## Built-in MCP Servers

### Firecrawl MCP (Local STDIO)
- **Type**: Local subprocess via STDIO
- **Startup**: Automatic with `langgraph dev`
- **Tools**: ~10 web scraping and crawling tools
- **Requirements**: `FIRECRAWL_API_KEY`, Node.js, npx

### Microsoft Learn MCP (Remote HTTP)
- **Type**: Remote server via streamable HTTP
- **Endpoint**: `https://learn.microsoft.com/api/mcp`
- **Authentication**: None required (public server)
- **Tools**: Microsoft Learn content search and processing

## Adding New MCP Servers

### Pattern 1: Remote HTTP Server (Recommended)
```python
def get_your_mcp_tools() -> List[object]:
    """Connect to a remote MCP server via HTTP."""
    server_config = {
        "your_server": {
            "transport": "streamable_http",
            "url": "https://your-mcp-server.com/api/mcp",
            "headers": {"Authorization": "Bearer your-token"}  # if needed
        }
    }
    
    print(f"[your_mcp] Connecting to remote server...")
    
    try:
        return _get_mcp_tools_sync(server_config)
    except Exception as e:
        print(f"[your_mcp] Connection failed: {type(e).__name__}: {e}")
        return []
```

### Pattern 2: Local STDIO Server
```python
def get_your_local_mcp_tools() -> List[object]:
    """Connect to a local MCP server via STDIO subprocess."""
    api_key = os.getenv("YOUR_API_KEY", "")
    if not api_key:
        print(f"[your_mcp] YOUR_API_KEY not found, skipping")
        return []
    
    server_config = {
        "your_server": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "your-mcp-package"],
            "env": {
                "YOUR_API_KEY": api_key,
                "PATH": os.environ.get("PATH", "")
            }
        }
    }
    
    print(f"[your_mcp] Starting local server...")
    
    try:
        return _get_mcp_tools_sync(server_config)
    except Exception as e:
        print(f"[your_mcp] Failed to start: {type(e).__name__}: {e}")
        return []
```

## Integration Steps

### 1. Add Your Function to `mcp_tools.py`
Copy one of the patterns above and customize for your MCP server.

### 2. Update the Combined Function
```python
def get_all_mcp_tools() -> List[object]:
    """Get all available MCP tools."""
    all_tools = []
    
    # Existing servers
    all_tools.extend(get_firecrawl_mcp_tools())
    all_tools.extend(get_microsoft_learn_mcp_tools())
    
    # Add your server
    all_tools.extend(get_your_mcp_tools())
    
    return all_tools
```

### 3. Use in Your Agent
```python
from deepagents.mcp_tools import get_all_mcp_tools

mcp_tools = get_all_mcp_tools()
agent = create_deep_agent(your_tools + mcp_tools, instructions)
```

## Best Practices

### ✅ **Recommended Approaches**
- **Remote HTTP servers** when available (more reliable)
- **Error handling** with graceful fallbacks
- **Environment variable validation** before connecting
- **Clear logging** for debugging connections

### ❌ **Avoid These Issues**
- **Complex subprocess management** (use simple STDIO pattern)
- **Hardcoded URLs or commands** (use environment variables)
- **Silent failures** (always log connection attempts)
- **Missing error handling** (always wrap in try/catch)

## Debugging MCP Connections

### Check Logs
Look for these patterns in your langgraph dev output:
```
[your_mcp] Connecting to remote server...
[your_mcp] Successfully connected! Got 5 tools
```

### Test Individual Servers
```python
# Test one server at a time
tools = get_firecrawl_mcp_tools()
print(f"Firecrawl tools: {len(tools)}")

tools = get_microsoft_learn_mcp_tools()  
print(f"Learn tools: {len(tools)}")
```

### Common Issues
- **STDIO failures**: Check Node.js, npx, and API key environment variables
- **HTTP failures**: Check internet connection and endpoint URLs
- **Import errors**: Ensure `langchain-mcp-adapters` is installed

## Example MCP Servers

### Working Examples in This Project
- **Firecrawl**: Web scraping via local STDIO
- **Microsoft Learn**: Documentation via remote HTTP

### Popular MCP Servers
- **GitHub MCP**: Repository access
- **Filesystem MCP**: Local file operations  
- **Database MCP**: SQL database access
- **Slack MCP**: Team communication

## References

- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [Model Context Protocol Spec](https://modelcontextprotocol.io/)
- [Microsoft Learn MCP Server](https://learn.microsoft.com/en-us/training/support/mcp)
- [Firecrawl MCP Documentation](https://docs.firecrawl.dev/)

---

**Pro Tip**: Start with remote HTTP servers when possible - they're more reliable than local STDIO subprocess management.