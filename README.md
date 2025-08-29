# 🧠🤖Deep Agents

langgraph dev --allow-blocking

Using an LLM to call tools in a loop is the simplest form of an agent. 
This architecture, however, can yield agents that are “shallow” and fail to plan and act over longer, more complex tasks. 
Applications like “Deep Research”, "Manus", and “Claude Code” have gotten around this limitation by implementing a combination of four things:
a **planning tool**, **sub agents**, access to a **file system**, and a **detailed prompt**.

<img src="deep_agents.png" alt="deep agent" width="600"/>

`deepagents` is a Python package that implements these in a general purpose way so that you can easily create a Deep Agent for your application.

**Acknowledgements: This project was primarily inspired by Claude Code, and initially was largely an attempt to see what made Claude Code general purpose, and make it even more so.**

## Installation

```bash
pip install deepagents
```

## Usage

(To run the example below, will need to `pip install tavily-python`)

```python
import os
from typing import Literal

from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Search tool to use to do research
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


# Prompt prefix to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""

# Create the agent
agent = create_deep_agent(
    [internet_search],
    research_instructions,
)

# Invoke the agent
result = agent.invoke({"messages": [{"role": "user", "content": "what is langgraph?"}]})
```

See [examples/research/research_agent.py](examples/research/research_agent.py) for a more complex example.

### Unstructured MCP Integration

For document processing (PDF, DOCX, PPTX, images, etc.), follow the guide in `complete_unstructured_integration_guide.md`.

Environment variables expected by the integration (place these in your project root `.env`):

```
# Unstructured MCP Configuration
UNSTRUCTURED_API_KEY=your-unstructured-api-key-here
UNSTRUCTURED_MCP_DIR=C:\\Users\\<you>\\DEV\\deepagents\\mcp-unstructured-server
UNSTRUCTURED_OUTPUT_DIR=C:\\Users\\<you>\\AppData\\Local\\Temp\\unstructured_output
```

On Windows, ensure the paths are absolute. The project uses a root `.venv` as its virtual environment; activate it before running examples.

The agent created with `create_deep_agent` is just a LangGraph graph - so you can interact with it (streaming, human-in-the-loop, memory, studio)
in the same way you would any LangGraph agent.

### Anthropic 1M Context (Claude Sonnet 4)

Organizations on Anthropic usage tier 4 (or with custom limits) can enable the 1M token context window for Claude Sonnet 4. This repository supports an opt-in toggle that adds the required beta header automatically.

Environment variables (place in project root `.env`):

```
# Enable 1M context (optional; defaults to off)
DEEPAGENTS_ENABLE_1M_CONTEXT=true

# Optional: increase request timeout for very large prompts (seconds)
DEEPAGENTS_REQUEST_TIMEOUT_SECONDS=300

# Anthropic credentials
ANTHROPIC_API_KEY=your-anthropic-key
```

Details:
- When `DEEPAGENTS_ENABLE_1M_CONTEXT` is true, the library sends `anthropic-beta: context-1m-2025-08-07` on all Anthropic requests.
- Default model remains `claude-sonnet-4-20250514` via `ChatAnthropic`.
- Long-context requests over 200K tokens incur premium pricing and have separate rate limits. Plan prompts accordingly and consider chunked RAG for cost/latency.

Note: You can keep this disabled by default and enable it only for workflows that truly benefit from very large prompts.

### Markdown → DOCX conversion and download

The library provides a backend tool to convert agent-created Markdown files to DOCX and return a signed download URL via Supabase Storage.

- Tool: `convert_and_download_docx`
- Storage bucket: `generated-exports` (private)
- Tracking table: `public.da_generated_exports`

Setup:
- Ensure environment variables in your project root `.env`:

```
SUPABASE_URL=...        # Your Supabase project URL
SUPABASE_SERVICE_ROLE_KEY=...  # Service role key for server-side upload/sign
```

Usage example (inside an agent run with VFS):

```python
from deepagents.tools import convert_and_download_docx

# state contains a VFS and a contextId
state = {
  "files": {"/work/learning_content.md": "# Title\n\nSome text..."},
  "contextId": "<uuid>"
}

result_json = convert_and_download_docx(
  state=state,
  vfs_md_path="/work/learning_content.md",
  approved_docx_filename="learning_content.docx",
  include_toc=True,  # optional
  reference_docx_path=None,  # optional path to a style template
)
# Returns JSON: { success, bucket, object_path, filename, size_bytes, signed_url, expires_in }
```

Notes:
- Conversion uses Pandoc via `pypandoc` and will attempt to download the Pandoc binary if missing.
- Images referenced by relative paths can be resolved by passing `resource_paths=["/work"]`.
- Signed URLs expire (default 1 hour). Generate a new link if needed.

## Creating a custom deep agent

There are three parameters you can pass to `create_deep_agent` to create your own custom deep agent.

### `tools` (Required)

The first argument to `create_deep_agent` is `tools`.
This should be a list of functions or LangChain `@tool` objects.
The agent (and any subagents) will have access to these tools.

### `instructions` (Required)

The second argument to `create_deep_agent` is `instructions`.
This will serve as part of the prompt of the deep agent.
Note that there is a [built in system prompt](src/deepagents/prompts.py) as well, so this is not the *entire* prompt the agent will see.

### `subagents` (Optional)

A keyword-only argument to `create_deep_agent` is `subagents`.
This can be used to specify any custom subagents this deep agent will have access to.
You can read more about why you would want to use subagents [here](#sub-agents)

`subagents` should be a list of dictionaries, where each dictionary follow this schema:

```python
class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]
    model_settings: NotRequired[dict[str, Any]]
```

- **name**: This is the name of the subagent, and how the main agent will call the subagent
- **description**: This is the description of the subagent that is shown to the main agent
- **prompt**: This is the prompt used for the subagent
- **tools**: This is the list of tools that the subagent has access to. By default will have access to all tools passed in, as well as all built-in tools.
- **model_settings**: Optional dictionary for per-subagent model configuration (inherits the main model when omitted).

To use it looks like:

```python
research_sub_agent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "prompt": sub_research_prompt,
}
subagents = [research_subagent]
agent = create_deep_agent(
    tools,
    prompt,
    subagents=subagents
)
```

### `model` (Optional)

By default, `deepagents` uses `"claude-sonnet-4-20250514"`. You can customize this by passing any [LangChain model object](https://python.langchain.com/docs/integrations/chat/).

#### Example: Using a Custom Model

Here's how to use a custom model (like OpenAI's `gpt-oss` model via Ollama):

(Requires `pip install langchain` and then `pip install langchain-ollama` for Ollama models)

```python
from deepagents import create_deep_agent

# ... existing agent definitions ...

model = init_chat_model(
    model="ollama:gpt-oss:20b",  
)
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    model=model,
    ...
)
```

#### Example: Per-subagent model override (optional)

Use a fast, deterministic model for a critique sub-agent, while keeping a different default model for the main agent and others:

```python
from deepagents import create_deep_agent

critique_sub_agent = {
    "name": "critique-agent",
    "description": "Critique the final report",
    "prompt": "You are a tough editor.",
    "model_settings": {
        "model": "anthropic:claude-3-5-haiku-20241022",
        "temperature": 0,
        "max_tokens": 8192
    }
}

agent = create_deep_agent(
    tools=[internet_search],
    instructions="You are an expert researcher...",
    model="claude-sonnet-4-20250514",  # default for main agent and other sub-agents
    subagents=[critique_sub_agent],
)
```

## Deep Agent Details

The below components are built into `deepagents` and helps make it work for deep tasks off-the-shelf.

### System Prompt

`deepagents` comes with a [built-in system prompt](src/deepagents/prompts.py). This is relatively detailed prompt that is heavily based on and inspired by [attempts](https://github.com/kn1026/cc/blob/main/claudecode.md) to [replicate](https://github.com/asgeirtj/system_prompts_leaks/blob/main/Anthropic/claude-code.md)
Claude Code's system prompt. It was made more general purpose than Claude Code's system prompt.
This contains detailed instructions for how to use the built-in planning tool, file system tools, and sub agents.
Note that part of this system prompt [can be customized](#instructions-required)

Without this default system prompt - the agent would not be nearly as successful at going as it is.
The importance of prompting for creating a "deep" agent cannot be understated.

### Planning Tool

`deepagents` comes with a built-in planning tool. This planning tool is very simple and is based on ClaudeCode's TodoWrite tool.
This tool doesn't actually do anything - it is just a way for the agent to come up with a plan, and then have that in the context to help keep it on track.

### File System Tools

`deepagents` comes with five built-in file system tools: `ls`, `edit_file`, `read_file`, `write_file`, `delete_file`.
These do not actually use a file system - rather, they mock out a file system using LangGraph's State object.
This means you can easily run many of these agents on the same machine without worrying that they will edit the same underlying files.

Right now the "file system" will only be one level deep (no sub directories).

These files can be passed in (and also retrieved) by using the `files` key in the LangGraph State object.

```python
agent = create_deep_agent(...)

result = agent.invoke({
    "messages": ...,
    # Pass in files to the agent using this key
    # "files": {"foo.txt": "foo", ...}
})

# Access any files afterwards like this
result["files"]
```

### Sub Agents

`deepagents` comes with the built-in ability to call sub agents (based on Claude Code).
It has access to a `general-purpose` subagent at all times - this is a subagent with the same instructions as the main agent and all the tools that is has access to.
You can also specify [custom sub agents](#subagents-optional) with their own instructions and tools.

Sub agents are useful for ["context quarantine"](https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html#context-quarantine) (to help not pollute the overall context of the main agent)
as well as custom instructions.

### Tool Interrupts

`deepagents` supports human-in-the-loop approval for tool execution. You can configure specific tools to require human approval before execution using the `interrupt_config` parameter. You can also customize the message prefix shown to users for each tool when approval is required.

The interrupt configuration uses four boolean parameters:
- `allow_ignore`: Whether the user can skip the tool call
- `allow_respond`: Whether the user can add a text response
- `allow_edit`: Whether the user can edit the tool arguments
- `allow_accept`: Whether the user can accept the tool call

Example usage:

```python
from deepagents import create_deep_agent
from langgraph.prebuilt.interrupt import HumanInterruptConfig

# Create agent with file operations requiring approval
agent = create_deep_agent(
    tools=[your_tools],
    instructions="Your instructions here",
    interrupt_config={
        "write_file": HumanInterruptConfig(
            allow_ignore=False,
            allow_respond=False,
            allow_edit=False,
            allow_accept=True,
        ),
    }
)
```

When a tool call requires approval, the agent will pause and wait for human input before proceeding. The message shown to users will include your custom prefix (or "Tool execution requires approval" by default) followed by the tool name and arguments. Multiple tool calls are processed in parallel, allowing you to review and approve multiple operations at once.

## MCP Integration

The `deepagents` library includes built-in support for MCP (Model Context Protocol) tools using the [LangChain MCP Adapter library](https://github.com/langchain-ai/langchain-mcp-adapters). This allows you to easily connect to MCP servers like Firecrawl for web scraping and Microsoft Learn for documentation processing.

### Installation

```bash
pip install langchain-mcp-adapters
```

### Built-in MCP Support

The library provides convenient functions to connect to MCP servers:

```python
from deepagents.mcp_tools import get_firecrawl_mcp_tools, get_microsoft_learn_mcp_tools, get_all_mcp_tools

# Get individual tool sets
firecrawl_tools = get_firecrawl_mcp_tools()  # Web scraping (auto-starts with langgraph dev)
learn_tools = get_microsoft_learn_mcp_tools()  # Microsoft Learn content & docs

# Or get all tools at once (recommended)
all_tools = get_all_mcp_tools()
```

### Environment Variables

Configure your MCP servers using environment variables:

```bash
# Firecrawl MCP (automatically starts with langgraph dev)
FIRECRAWL_API_KEY=your-firecrawl-api-key
FIRECRAWL_MCP_COMMAND=npx
FIRECRAWL_MCP_ARGS=-y firecrawl-mcp
```

### How It Works

When you run `langgraph dev`, the system connects to both MCP servers:

**Firecrawl MCP (Local STDIO):**
- **Automatic startup**: No manual server management required
- **Reliable connection**: Uses subprocess management 
- **10+ tools**: Web scraping, crawling, and content extraction

**Microsoft Learn MCP (Remote HTTP):**
- **Public server**: Connects to [Microsoft's Learn MCP endpoint](https://learn.microsoft.com/en-us/training/support/mcp)
- **No authentication**: Publicly available, no API key required
- **Documentation tools**: Search and process Microsoft Learn content for markdown conversion

### Custom MCP Client

For additional MCP servers, create your own client:

```python
import asyncio
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent

async def main():
    # Configure multiple MCP servers via STDIO
    client = MultiServerMCPClient({
        "firecrawl": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "firecrawl-mcp"],
            "env": {
                "FIRECRAWL_API_KEY": "your-firecrawl-api-key",
                "PATH": os.environ.get("PATH", "")
            }
        },
        "replicate": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "replicate-mcp"], 
            "env": {
                "REPLICATE_API_TOKEN": "your-replicate-token",
                "PATH": os.environ.get("PATH", "")
            }
        }
    })
    
    # Get all tools from all servers
    mcp_tools = await client.get_tools()

    # Create agent with MCP tools
    agent = create_deep_agent(
        tools=mcp_tools,
        instructions="You are a helpful assistant with access to web scraping and AI generation tools."
    )

    # Use the agent
    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": "Scrape https://example.com and summarize it"}]},
        stream_mode="values"
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()

asyncio.run(main())
```

## Prompt Caching (Anthropic) and Node Caching (LangGraph)

`deepagents` supports Anthropic prompt caching strategies and LangGraph node-level caching to reduce latency and costs for repeated content.

### Anthropic prompt caching helpers

Use helpers in `deepagents/anthropic_cache.py` to mark cache breakpoints:

```python
from deepagents.anthropic_cache import (
    add_cache_control_to_tools,
    build_cached_system_blocks,
    build_cached_message_blocks,
)

# 1) Cache all tools with a 1-hour TTL (mark last tool)
tools_with_cache = add_cache_control_to_tools(tools, ttl="1h")

# 2) Cache system instructions + base prompt with a 1-hour TTL
system_blocks = build_cached_system_blocks(instructions, base_prompt_text, ttl="1h")

# 3) Cache large RAG bundle and the final user block with a 5-minute TTL
rag_context_text = "... large document excerpts ..."
final_question = "Please analyze ..."
user_content_blocks = build_cached_message_blocks([rag_context_text, final_question], ttl="5m")

# Assemble request for Anthropic Messages API
payload = {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "tools": tools_with_cache,
    "system": system_blocks,
    "messages": [
        {"role": "user", "content": user_content_blocks}
    ],
}
```

Breakpoint order should follow Anthropic’s prefix order: tools → system → messages. Ensure cacheable segments meet model minimums (≥1024 tokens for Sonnet/Opus; ≥2048 for Haiku).

Recommended TTLs:
- Tools & System: `1h`
- RAG bundles & Conversation tail: `5m`

#### Learning example: make cached user messages with RAG bundles

In the learning example, use the convenience function to build a cache-marked user turn that includes large RAG context plus a question:

```python
from examples.learning.learning_agent import make_cached_user_message, agent

rag_texts = ["...long doc excerpt 1...", "...long doc excerpt 2..."]
user_msg = make_cached_user_message(rag_texts, "Summarize the key differences", ttl="5m")

result = agent.invoke({
    "messages": [user_msg],
})
```

### LangGraph node-level caching

For deterministic nodes that call Supabase-backed endpoints, use short TTL caches (30–120s) keyed by inputs (e.g., `context_id`, `query`, pagination). The built-in RAG tool functions (`list_documents_with_context`, `search_documents_with_context`) include lightweight TTL caches to avoid duplicate calls across rapid successive turns.

Notes:
- Keep tool schema ordering stable within a session to avoid invalidating tool-level cache.
- Avoid toggling images or thinking settings mid-session when depending on message-level cache.
- Add additional breakpoints if you exceed ~20 blocks before your final breakpoint.

## Roadmap
- [ ] Allow users to customize full system prompt
- [ ] Code cleanliness (type hinting, docstrings, formating)
- [ ] Allow for more of a robust virtual filesystem
- [ ] Create an example of a deep coding agent built on top of this
- [ ] Benchmark the example of [deep research agent](examples/research/research_agent.py)
