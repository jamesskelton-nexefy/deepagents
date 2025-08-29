from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import NotRequired, Annotated, Optional
from typing import Literal
from typing_extensions import TypedDict


class Todo(TypedDict):
    """Todo to track."""

    content: str
    status: Literal["pending", "in_progress", "completed"]


def file_reducer(l, r):
    print(f"🔄 REDUCER DEBUG: file_reducer called")
    print(f"🔄 REDUCER DEBUG: l (left/current state) = {l}")
    print(f"🔄 REDUCER DEBUG: r (right/new update) = {r}")
    
    if l is None:
        print(f"🔄 REDUCER DEBUG: Left state is None, returning right state: {r}")
        return r
    elif r is None:
        print(f"🔄 REDUCER DEBUG: Right state is None, returning left state: {l}")
        return l
    else:
        # Merge dictionaries, but filter out files marked for deletion (None values)
        merged = {**l, **r}
        print(f"🔄 REDUCER DEBUG: Raw merged state: {merged}")
        
        filtered = {k: v for k, v in merged.items() if v is not None}
        print(f"🔄 REDUCER DEBUG: Filtered state (removed None values): {filtered}")
        return filtered


class DeepAgentState(AgentState):
    todos: NotRequired[list[Todo]]
    files: Annotated[NotRequired[dict[str, Optional[str]]], file_reducer]
    contextId: NotRequired[str]
