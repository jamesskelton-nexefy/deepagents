from langchain_anthropic import ChatAnthropic
import os


_BETA_HEADER_VALUE = "context-1m-2025-08-07"
_ENV_ENABLE_1M = "DEEPAGENTS_ENABLE_1M_CONTEXT"
_ENV_TIMEOUT = "DEEPAGENTS_REQUEST_TIMEOUT_SECONDS"
_DEFAULT_MODEL = "claude-sonnet-4-20250514"


def get_default_model():
    enable_1m = os.getenv(_ENV_ENABLE_1M, "false").lower() in ["1", "true", "yes", "on"]
    timeout_env = os.getenv(_ENV_TIMEOUT)
    timeout = None
    if timeout_env:
        try:
            timeout = float(timeout_env)
        except ValueError:
            timeout = None

    default_headers = None
    if enable_1m:
        # Instruct Anthropic API to enable 1M context for eligible workspaces
        default_headers = {"anthropic-beta": _BETA_HEADER_VALUE}

    return ChatAnthropic(
        model_name=_DEFAULT_MODEL,
        max_tokens=64000,
        default_headers=default_headers,
        default_request_timeout=timeout,
    )
