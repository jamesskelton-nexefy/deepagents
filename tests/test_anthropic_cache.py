from deepagents.anthropic_cache import (
    add_cache_control_to_tools,
    build_cached_system_blocks,
    build_cached_message_blocks,
)


def test_add_cache_control_to_tools_marks_last_only():
    tools = [
        {"name": "t1", "description": "a", "input_schema": {"type": "object"}},
        {"name": "t2", "description": "b", "input_schema": {"type": "object"}},
    ]
    out = add_cache_control_to_tools(tools, ttl="1h")
    assert "cache_control" not in out[0]
    assert out[1]["cache_control"]["type"] == "ephemeral"
    assert out[1]["cache_control"]["ttl"] == "1h"


def test_build_cached_system_blocks_applies_breakpoint_on_second_block():
    blocks = build_cached_system_blocks("instr", "base", ttl="1h")
    assert blocks[0]["type"] == "text"
    assert "cache_control" not in blocks[0]
    assert blocks[1]["cache_control"]["ttl"] == "1h"


def test_build_cached_message_blocks_marks_only_last():
    blocks = build_cached_message_blocks(["ctx", "question"], ttl="5m")
    assert "cache_control" not in blocks[0]
    assert blocks[1]["cache_control"]["type"] == "ephemeral"
    assert blocks[1]["cache_control"]["ttl"] == "5m"


