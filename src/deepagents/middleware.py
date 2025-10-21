"""DeepAgents implemented as Middleware"""

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState, ModelRequest, SummarizationMiddleware
from langchain.agents.middleware.prompt_caching import AnthropicPromptCachingMiddleware
from langchain_core.tools import BaseTool, tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain.chat_models import init_chat_model
from langgraph.types import Command
from langgraph.runtime import Runtime
from langchain.tools.tool_node import InjectedState
from typing import Annotated
from deepagents.state import PlanningState, FilesystemState
from deepagents.tools import write_todos, ls, read_file, write_file, edit_file, request_document_upload
from deepagents.prompts import WRITE_TODOS_SYSTEM_PROMPT, TASK_SYSTEM_PROMPT, FILESYSTEM_SYSTEM_PROMPT, TASK_TOOL_DESCRIPTION, BASE_AGENT_PROMPT
from deepagents.types import SubAgent, CustomSubAgent

###################################
# Base class with async compatibility
###################################


class AsyncSafeAgentMiddleware(AgentMiddleware):
    """Extends AgentMiddleware to support async LangGraph calls safely."""

    def wrap_model_call(self, request, handler):
        """Sync version - just pass through."""
        return handler(request)

    async def awrap_model_call(self, request, handler):
        """Async version - just pass through."""
        return await handler(request)

        
###########################
# Thread ID Middleware
###########################

class ThreadIdMiddleware(AsyncSafeAgentMiddleware):
    """Middleware to inject thread_id from config into state.
    
    This middleware ensures thread_id is available in state for tools like retrieve_context.
    It checks:
    1. If thread_id is already in state (passed via input) - keeps it
    2. If not, tries to extract from runtime config (LangGraph Platform)
    3. If not found, logs a warning
    """
    
    def before_model(self, state: AgentState, runtime: Runtime):
        """Inject thread_id from runtime config into state if not already present."""
        import sys
        
        # Check if thread_id is already in state (passed via input)
        existing_thread_id = state.get("thread_id")
        if existing_thread_id:
            print(f"DEBUG ThreadIdMiddleware: thread_id already in state: {existing_thread_id}", file=sys.stderr)
            return None  # Don't override existing thread_id
        
        # Try to extract thread_id from runtime config
        thread_id = None
        
        if runtime:
            # Try runtime.config (most common for LangGraph Platform)
            if hasattr(runtime, 'config') and runtime.config:
                if isinstance(runtime.config, dict):
                    # Try configurable.thread_id
                    thread_id = runtime.config.get('configurable', {}).get('thread_id')
                elif hasattr(runtime.config, 'get'):
                    thread_id = runtime.config.get('thread_id')
                    if not thread_id:
                        configurable = getattr(runtime.config, 'configurable', {})
                        if isinstance(configurable, dict):
                            thread_id = configurable.get('thread_id')
            
            # Try runtime.thread_id directly
            if not thread_id and hasattr(runtime, 'thread_id'):
                thread_id = runtime.thread_id
        
        # Debug logging
        if thread_id:
            print(f"DEBUG ThreadIdMiddleware: extracted thread_id from runtime: {thread_id}", file=sys.stderr)
            return {"thread_id": thread_id}
        else:
            print(f"DEBUG ThreadIdMiddleware: No thread_id found in runtime config", file=sys.stderr)
            print(f"DEBUG ThreadIdMiddleware: runtime type = {type(runtime)}", file=sys.stderr)
            if hasattr(runtime, 'config'):
                print(f"DEBUG ThreadIdMiddleware: config = {runtime.config}", file=sys.stderr)
        
        return None


###########################
# Planning Middleware
###########################

class PlanningMiddleware(AgentMiddleware):
    state_schema = PlanningState
    tools = [write_todos]

    def modify_model_request(self, request: ModelRequest, agent_state: PlanningState, runtime: Runtime) -> ModelRequest:
        request.system_prompt = request.system_prompt + "\n\n" + WRITE_TODOS_SYSTEM_PROMPT
        return request

###########################
# Filesystem Middleware
###########################

class FilesystemMiddleware(AgentMiddleware):
    state_schema = FilesystemState
    tools = [ls, read_file, write_file, edit_file, request_document_upload]

    def modify_model_request(self, request: ModelRequest, agent_state: FilesystemState, runtime: Runtime) -> ModelRequest:
        request.system_prompt = request.system_prompt + "\n\n" + FILESYSTEM_SYSTEM_PROMPT
        return request

###########################
# SubAgent Middleware
###########################

class SubAgentMiddleware(AgentMiddleware):
    def __init__(
        self,
        default_subagent_tools: list[BaseTool] = [],
        subagents: list[SubAgent | CustomSubAgent] = [],
        model=None,
        is_async=False,
    ) -> None:
        super().__init__()
        task_tool = create_task_tool(
            default_subagent_tools=default_subagent_tools,
            subagents=subagents,
            model=model,
            is_async=is_async,
        )
        self.tools = [task_tool]

    def modify_model_request(self, request: ModelRequest, agent_state: AgentState, runtime: Runtime) -> ModelRequest:
        request.system_prompt = request.system_prompt + "\n\n" + TASK_SYSTEM_PROMPT
        return request

###################################
# Async-Safe Wrapper Middleware
###################################


class AsyncSummarizationMiddleware(AsyncSafeAgentMiddleware):
    """Async-safe wrapper for SummarizationMiddleware."""

    def __init__(self, model, max_tokens_before_summary=120000, messages_to_keep=20):
        super().__init__()
        self._middleware = SummarizationMiddleware(
            model=model,
            max_tokens_before_summary=max_tokens_before_summary,
            messages_to_keep=messages_to_keep,
        )

    def modify_model_request(
        self, request: ModelRequest, agent_state: AgentState, runtime: Runtime
    ) -> ModelRequest:
        """Delegate to the wrapped middleware."""
        return self._middleware.modify_model_request(request, agent_state, runtime)


class AsyncAnthropicPromptCachingMiddleware(AsyncSafeAgentMiddleware):
    """Async-safe wrapper for AnthropicPromptCachingMiddleware."""

    def __init__(self, ttl="5m", unsupported_model_behavior="ignore"):
        super().__init__()
        self._middleware = AnthropicPromptCachingMiddleware(
            ttl=ttl, unsupported_model_behavior=unsupported_model_behavior
        )

    def modify_model_request(
        self, request: ModelRequest, agent_state: AgentState, runtime: Runtime
    ) -> ModelRequest:
        """Delegate to the wrapped middleware."""
        return self._middleware.modify_model_request(request, agent_state, runtime)

def _get_agents(
    default_subagent_tools: list[BaseTool],
    subagents: list[SubAgent | CustomSubAgent],
    model
):
    default_subagent_middleware = [
        ThreadIdMiddleware(),  # Subagents need thread_id to access documents
        PlanningMiddleware(),
        FilesystemMiddleware(),
        # TODO: Add this back when fixed
        SummarizationMiddleware(
            model=model,
            max_tokens_before_summary=120000,
            messages_to_keep=20,
        ),
        AnthropicPromptCachingMiddleware(ttl="5m", unsupported_model_behavior="ignore"),
    ]
    agents = {
        "general-purpose": create_agent(
            model,
            system_prompt=BASE_AGENT_PROMPT,
            tools=default_subagent_tools,
            checkpointer=False,
            middleware=default_subagent_middleware
        )
    }
    for _agent in subagents:
        if "graph" in _agent:
            agents[_agent["name"]] = _agent["graph"]
            continue
        if "tools" in _agent:
            _tools = _agent["tools"]
        else:
            _tools = default_subagent_tools.copy()
        # Resolve per-subagent model: can be instance or dict
        if "model" in _agent:
            agent_model = _agent["model"]
            if isinstance(agent_model, dict):
                # Dictionary settings - create model from config
                sub_model = init_chat_model(**agent_model)
            else:
                # Model instance - use directly
                sub_model = agent_model
        else:
            # Fallback to main model
            sub_model = model
        if "middleware" in _agent:
            _middleware = [*default_subagent_middleware, *_agent["middleware"]]
        else:
            _middleware = default_subagent_middleware
        agents[_agent["name"]] = create_agent(
            sub_model,
            system_prompt=_agent["prompt"],
            tools=_tools,
            middleware=_middleware,
            checkpointer=False,
        )
    return agents


def _get_subagent_description(subagents: list[SubAgent | CustomSubAgent]):
    return [f"- {_agent['name']}: {_agent['description']}" for _agent in subagents]


def create_task_tool(
    default_subagent_tools: list[BaseTool],
    subagents: list[SubAgent | CustomSubAgent],
    model,
    is_async: bool = False,
):
    agents = _get_agents(
        default_subagent_tools, subagents, model
    )
    other_agents_string = _get_subagent_description(subagents)

    if is_async:
        @tool(
            description=TASK_TOOL_DESCRIPTION.format(other_agents=other_agents_string)
        )
        async def task(
            description: str,
            subagent_type: str,
            state: Annotated[dict, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
        ):
            from langgraph.store import get_stream_writer
            from datetime import datetime
            
            if subagent_type not in agents:
                return f"Error: invoked agent of type {subagent_type}, the only allowed types are {[f'`{k}`' for k in agents]}"
            
            sub_agent = agents[subagent_type]
            writer = get_stream_writer()
            
            # Emit subagent start event
            writer({
                "type": "subagent_start",
                "subagent": subagent_type,
                "task": description,
                "timestamp": datetime.now().isoformat()
            })
            
            # Preserve thread_id from parent state so subagent can access same documents
            subagent_state = {"messages": [{"role": "user", "content": description}]}
            if "thread_id" in state:
                subagent_state["thread_id"] = state["thread_id"]
            
            # Stream from sub-agent with multiple modes
            async for stream_mode, chunk in sub_agent.astream(
                subagent_state,
                stream_mode=["updates", "messages", "custom"]
            ):
                # Forward all streaming events with subagent context
                writer({
                    "type": f"subagent_{stream_mode}",
                    "subagent": subagent_type,
                    "data": chunk,
                    "stream_mode": stream_mode
                })
            
            # Emit subagent end event
            writer({
                "type": "subagent_end", 
                "subagent": subagent_type,
                "timestamp": datetime.now().isoformat()
            })
            
            # Get final result
            result = await sub_agent.ainvoke(subagent_state)
            state_update = {}
            for k, v in result.items():
                if k not in ["todos", "messages"]:
                    state_update[k] = v
            return Command(
                update={
                    **state_update,
                    "messages": [
                        ToolMessage(
                            result["messages"][-1].content, tool_call_id=tool_call_id
                        )
                    ],
                }
            )
    else: 
        @tool(
            description=TASK_TOOL_DESCRIPTION.format(other_agents=other_agents_string)
        )
        def task(
            description: str,
            subagent_type: str,
            state: Annotated[dict, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
        ):
            if subagent_type not in agents:
                return f"Error: invoked agent of type {subagent_type}, the only allowed types are {[f'`{k}`' for k in agents]}"
            sub_agent = agents[subagent_type]
            
            # Preserve thread_id from parent state so subagent can access same documents
            subagent_state = {"messages": [{"role": "user", "content": description}]}
            if "thread_id" in state:
                subagent_state["thread_id"] = state["thread_id"]
            
            result = sub_agent.invoke(subagent_state)
            state_update = {}
            for k, v in result.items():
                if k not in ["todos", "messages"]:
                    state_update[k] = v
            return Command(
                update={
                    **state_update,
                    "messages": [
                        ToolMessage(
                            result["messages"][-1].content, tool_call_id=tool_call_id
                        )
                    ],
                }
            )
    return task
