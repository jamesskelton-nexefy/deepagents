from deepagents.anthropic_tokens import count_input_tokens


def test_count_tokens_fallback_plain_text():
    messages = [{"role": "user", "content": "hello world"}]
    tokens = count_input_tokens("claude-sonnet-4-20250514", messages)
    assert isinstance(tokens, int)
    assert tokens >= 1


def test_count_tokens_blocks_fallback():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "foo"},
                {"type": "text", "text": "bar baz"},
            ],
        }
    ]
    tokens = count_input_tokens("claude-sonnet-4-20250514", messages)
    assert tokens >= 1


