"""
Utilities for constructing Anthropic-compatible message and tools payloads
with prompt caching metadata (cache_control) applied to specific blocks.

These helpers are opt-in and do not require changing LangGraph orchestration.

Usage example (pseudo):

    from deepagents.anthropic_cache import (
        add_cache_control_to_tools,
        build_cached_system_blocks,
        build_cached_message_blocks,
    )

    tools_with_cache = add_cache_control_to_tools(tools, ttl="1h")
    system_blocks = build_cached_system_blocks(
        instructions_text, base_prompt_text, ttl="1h"
    )
    rag_blocks = build_cached_message_blocks([rag_bundle_text], ttl="5m")
    tail_blocks = build_cached_message_blocks([final_user_question], ttl="5m")

Then assemble the request as per Anthropic Messages API with:
  - tools = tools_with_cache
  - system = system_blocks + (optional static blocks)
  - messages = [... prior turns ..., {role: "user", content: rag_blocks + tail_blocks}]
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence


def _text_block(text: str, cache_ttl: str | None = None) -> Dict[str, Any]:
    """Create a text block with optional cache_control metadata."""
    block: Dict[str, Any] = {"type": "text", "text": text}
    if cache_ttl:
        block["cache_control"] = {"type": "ephemeral", "ttl": cache_ttl}
    return block


def add_cache_control_to_tools(
    tools: Sequence[Dict[str, Any]], ttl: str = "1h"
) -> List[Dict[str, Any]]:
    """Return a new tools list where the final tool has cache_control applied.

    Anthropic caches prefix content up to and including the block marked with
    cache_control. Marking the last tool caches all preceding tool definitions
    as a single prefix segment.
    """
    if not tools:
        return []

    result: List[Dict[str, Any]] = [dict(t) for t in tools]
    # Apply cache_control to the final tool only
    result[-1] = {**result[-1], "cache_control": {"type": "ephemeral", "ttl": ttl}}
    return result


def build_cached_system_blocks(
    instructions_text: str,
    base_prompt_text: str,
    ttl: str = "1h",
) -> List[Dict[str, Any]]:
    """Build system content blocks with cache_control applied.

    The returned list is intended for the Anthropic "system" parameter.
    The second block receives cache_control, ensuring both blocks are covered by
    the cached prefix.
    """
    blocks: List[Dict[str, Any]] = []
    # First block (no cache_control) to allow automatic back-check and longest-prefix matching
    blocks.append(_text_block(instructions_text))
    # Second block marks end of reusable system content
    blocks.append(_text_block(base_prompt_text, cache_ttl=ttl))
    return blocks


def build_cached_message_blocks(
    texts: Iterable[str], ttl: str = "5m"
) -> List[Dict[str, Any]]:
    """Build message content blocks where only the final block is cache-marked.

    This is useful for composing a message that ends with a cache breakpoint,
    such as RAG context followed by the final user question.
    """
    texts_list = list(texts)
    if not texts_list:
        return []

    blocks: List[Dict[str, Any]] = []
    # All but last: plain text blocks
    for t in texts_list[:-1]:
        blocks.append(_text_block(t))
    # Last block: mark as cache breakpoint
    blocks.append(_text_block(texts_list[-1], cache_ttl=ttl))
    return blocks


def build_conversation_tail_block(text: str, ttl: str = "5m") -> Dict[str, Any]:
    """Convenience for caching the last message block in a turn."""
    return _text_block(text, cache_ttl=ttl)


