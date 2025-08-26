# Manual MCP Server Startup Guide

This guide helps you start Firecrawl and Replicate MCP servers independently before running your LangGraph agent.

## Why Manual Startup?

Due to protocol version compatibility issues between the Python MCP client and Node.js MCP servers, we use a manual startup approach where:
1. You start the MCP servers in separate terminals
2. The LangGraph agent connects to the already-running servers
3. This avoids protocol handshake timeouts during agent initialization

## Prerequisites

1. Activate your virtual environment:
   ```bash
   source .venv/Scripts/activate  # Windows Git Bash
   # or
   .venv\Scripts\activate.bat     # Windows CMD
   ```

2. Ensure your `.env` file has the required API keys:
   ```
   FIRECRAWL_API_KEY=fc-your-api-key
   REPLICATE_API_TOKEN=r8_your-api-token
   ```

## Step 1: Configure Firecrawl MCP Server (SSE Mode - Recommended)

You have two options for SSE mode:

### Option A: Remote SSE Endpoint (Easiest - No Local Server Needed)

Update your `.env` file to use Firecrawl's hosted SSE endpoint:
```bash
FIRECRAWL_SSE_MODE=true
FIRECRAWL_SSE_URL=https://mcp.firecrawl.dev/fc-3c7e4756fa984adbaccd7c135eaf2f51/sse
```

With this option, **no local server startup is required**. Skip to Step 2.

### Option B: Local SSE Server

Open a **new terminal window** and run:

```bash
# Navigate to your project
cd /c/Users/JamesSkelton/DEV/deepagents

# Activate venv
source .venv/Scripts/activate

# Start Firecrawl MCP server in SSE mode
env SSE_LOCAL=true FIRECRAWL_API_KEY=fc-3c7e4756fa984adbaccd7c135eaf2f51 npx -y firecrawl-mcp
```

**Expected output for SSE mode:**
```
Initializing FireCrawl MCP Server...
Running in SSE mode on http://localhost:3000/sse
[info] FireCrawl MCP Server initialized successfully
[info] Configuration: API URL: default
FireCrawl MCP Server running on SSE endpoint
```

**If you see "Running in stdio mode" instead:**
This means the SSE_LOCAL environment variable isn't being recognized. Try these alternatives:

1. Use the remote SSE endpoint instead:
   ```bash
   # No local server needed - uses Firecrawl's hosted SSE endpoint
   # Update your .env to use: FIRECRAWL_SSE_URL=https://mcp.firecrawl.dev/fc-3c7e4756fa984adbaccd7c135eaf2f51/sse
   ```

2. Or try running with explicit export:
   ```bash
   export SSE_LOCAL=true
   export FIRECRAWL_API_KEY=fc-3c7e4756fa984adbaccd7c135eaf2f51
   npx -y firecrawl-mcp
   ```

The server will be available at: `http://localhost:3000/sse` (local) or the remote URL

Keep this terminal **open and running**.

### Alternative: STDIO Mode (Fallback)

If SSE mode doesn't work, you can use the traditional STDIO mode:

```bash
# Start Firecrawl MCP server in STDIO mode
FIRECRAWL_API_KEY=fc-3c7e4756fa984adbaccd7c135eaf2f51 npx -y firecrawl-mcp
```

**Note:** You'll need to set `FIRECRAWL_SSE_MODE=false` in your `.env` file for STDIO mode.

## Step 2: Start Replicate MCP Server

Open **another new terminal window** and run:

```bash
# Navigate to your project
cd /c/Users/JamesSkelton/DEV/deepagents

# Activate venv
source .venv/Scripts/activate

# Start Replicate MCP server
REPLICATE_API_TOKEN=your_replicate_api_token_here npx -y replicate-mcp
```

**Expected output:**
```
MCP Server starting with 35 tools: [
  'list_collections',
  'get_collections',
  'create_deployments',
  # ... (full list of 35 tools)
]
MCP Server running on stdio
```

Keep this terminal **open and running**.

## Step 3: Start LangGraph Development Server

In your **main terminal**, start the LangGraph dev server:

```bash
# Navigate to the research example
cd examples/research

# Start LangGraph dev server
langgraph dev
```

**Note:** If you're using the remote SSE endpoint (Option A), you don't need any local Firecrawl server running. If using local SSE (Option B), ensure your local server terminal is still running.

## Verification

1. **Firecrawl MCP Server (SSE Mode)**:
   - **Option A (Remote)**: No local server needed - connection will be made directly to `https://mcp.firecrawl.dev/your-api-key/sse`
   - **Option B (Local)**: Should show "FireCrawl MCP Server running on SSE endpoint" and be accessible at `http://localhost:3000/sse`
2. **Replicate MCP Server**: Should show "MCP Server running on stdio" with 35 tools listed
3. **LangGraph Dev Server**: Should start without MCP-related errors and successfully connect to the configured Firecrawl SSE endpoint

## Troubleshooting

### Server Won't Start
- Ensure API keys are correct
- Check that `npx` is available: `npx --version`
- Try absolute path: `"C:\Program Files\nodejs\npx.cmd" -y firecrawl-mcp`

### SSE Connection Issues
- Verify the Firecrawl SSE server is running on `http://localhost:3000/sse`
- Test the endpoint manually: open `http://localhost:3000/sse` in a browser
- Check that `FIRECRAWL_SSE_MODE=true` is set in your `.env` file
- Ensure `SSE_LOCAL=true` environment variable is set when starting the server

### STDIO Connection Issues (Fallback)
- Ensure all three terminals are in the same project directory
- Verify the servers are still running (haven't crashed)
- Check that environment variables are properly set
- Set `FIRECRAWL_SSE_MODE=false` in `.env` to use STDIO mode

### Protocol Errors
- SSE mode often resolves protocol version compatibility issues
- If SSE connection fails, try the STDIO fallback mode
- If you still see timeouts, restart the servers

## Notes

- **Keep server terminals open**: Closing them stops the MCP servers
- **Restart if needed**: If servers crash, just restart them using the commands above
- **Environment isolation**: Each terminal should use the same virtual environment
