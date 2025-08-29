import os
from importlib import reload


def test_beta_header_toggle(monkeypatch):
    monkeypatch.setenv("DEEPAGENTS_ENABLE_1M_CONTEXT", "true")
    from deepagents import model as model_module
    reload(model_module)
    llm = model_module.get_default_model()
    # `default_headers` is a public attribute on ChatAnthropic
    headers = getattr(llm, "default_headers", None)
    assert isinstance(headers, dict) and headers.get("anthropic-beta")


def test_beta_header_disabled(monkeypatch):
    monkeypatch.delenv("DEEPAGENTS_ENABLE_1M_CONTEXT", raising=False)
    from deepagents import model as model_module
    reload(model_module)
    llm = model_module.get_default_model()
    headers = getattr(llm, "default_headers", None)
    assert headers is None


