## MCP Integration: Firecrawl + Replicate (Concise Guide)

This repo wires Firecrawl and Replicate MCP servers into the research agent via `langchain_mcp`. The agent will automatically pick up all tools exposed by these MCP servers.

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

### 2) Install dependencies (for the example)

```bash
pip install -r examples/research/requirements.txt
```

This installs `langchain-mcp` and `python-dotenv` in addition to the example deps.

### 3) Prepare environment variables

Copy `.env.example` to `.env` and set real values:

- `TAVILY_API_KEY`: Required for the included web search tool.
- `FIRECRAWL_API_KEY`: Required by the Firecrawl MCP server.
- `REPLICATE_API_TOKEN`: Required by the Replicate MCP server.

Optional (override the startup commands if needed):
- `FIRECRAWL_MCP_COMMAND` (default: `npx`)
- `FIRECRAWL_MCP_ARGS` (default: `-y @modelcontextprotocol/server-firecrawl`)
- `REPLICATE_MCP_COMMAND` (default: `npx`)
- `REPLICATE_MCP_ARGS` (default: `-y @modelcontextprotocol/server-replicate`)

Notes:
- These defaults assume Node.js is installed and that the official MCP server packages are available via `npx`. If the upstream package names change, update `*_MCP_ARGS` accordingly.
- Only the necessary API env vars are forwarded to the MCP servers.

### 4) How it works

- `src/deepagents/mcp_tools.py` uses `langchain_mcp` to spawn MCP servers as subprocesses and returns all tools from each server as LangChain tools.
- `examples/research/research_agent.py` loads `.env`, then adds both MCP tool sets to the agent.

### 5) Running the example

```bash
# From repo root
source .venv/bin/activate
python -m pip install -r examples/research/requirements.txt
cp .env.example .env  # then edit .env with your keys
python examples/research/research_agent.py  # or import and invoke in your app
```

### 6) Verifying tools are available

When the research agent is created, it fetches tools from:
- Firecrawl MCP (requires `FIRECRAWL_API_KEY`)
- Replicate MCP (requires `REPLICATE_API_TOKEN`)

If a server fails to start or connect, its tools are skipped and a message is printed. Ensure Node.js, `npx`, and the API keys are configured.

### 7) References

- LangChain MCP Toolkit: search for `langchain_mcp` in the LangChain docs
- Firecrawl docs: `https://docs.firecrawl.dev/`
- Replicate docs: `https://replicate.com/docs`

Keep packages up to date to track the latest MCP server names and features.