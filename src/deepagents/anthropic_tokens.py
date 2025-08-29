import os
from typing import Any, Dict, List, Optional


def count_input_tokens(
    model: str,
    messages: List[Dict[str, Any]],
    system: Optional[List[Dict[str, Any]] | str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    include_1m_beta: bool = False,
) -> int:
    """Count input tokens using Anthropic's token counting API.

    Falls back to a rough estimator if the Anthropic SDK is unavailable.
    Set include_1m_beta=True to mirror 1M-context header in the count call.
    """
    try:
        from anthropic import Anthropic
        client = Anthropic()

        extra_headers = None
        if include_1m_beta:
            extra_headers = {"anthropic-beta": "context-1m-2025-08-07"}

        resp = client.messages.count_tokens(
            model=model,
            messages=messages,
            system=system,
            tools=tools,
            extra_headers=extra_headers,
        )
        return int(getattr(resp, "input_tokens", 0))
    except Exception:
        # Fallback heuristic: assume ~4 chars per token
        def _len_msg(msg: Dict[str, Any]) -> int:
            content = msg.get("content", "")
            if isinstance(content, str):
                return len(content)
            if isinstance(content, list):
                total = 0
                for block in content:
                    if isinstance(block, dict):
                        t = block.get("text", "")
                        if isinstance(t, str):
                            total += len(t)
                return total
            return 0

        total_chars = sum(_len_msg(m) for m in messages)
        if isinstance(system, str):
            total_chars += len(system)
        elif isinstance(system, list):
            for block in system:
                if isinstance(block, dict):
                    t = block.get("text", "")
                    if isinstance(t, str):
                        total_chars += len(t)
        # very rough conversion
        return max(1, total_chars // 4)


