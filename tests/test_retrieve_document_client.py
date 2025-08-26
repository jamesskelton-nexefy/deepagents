import os
import types


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def test_retrieve_document_requires_identifiers(monkeypatch):
    # Ensure imports won't fail
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    from examples.research.learning_agent import retrieve_document  # type: ignore

    try:
        retrieve_document(document_id="", context_id="", filename="")
        assert False, "Expected ValueError when identifiers are missing"
    except ValueError:
        pass


def test_retrieve_document_builds_payload_by_id(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    sent = {}

    def fake_post(url, headers=None, json=None):
        sent["url"] = url
        sent["headers"] = headers
        sent["json"] = json
        return DummyResponse(200, {"ok": True})

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    from examples.research.learning_agent import retrieve_document  # type: ignore

    out = retrieve_document(document_id="doc-123")
    assert out == {"ok": True}
    assert sent["url"].endswith("/functions/v1/retrieve_document")
    assert sent["json"]["document_id"] == "doc-123"
    assert sent["json"]["format"] == "text"
    assert "Authorization" in sent["headers"]


def test_retrieve_document_builds_payload_by_name_version(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    captured = {}

    def fake_post(url, headers=None, json=None):
        captured["json"] = json
        return DummyResponse(200, {"ok": True})

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    from examples.research.learning_agent import retrieve_document  # type: ignore

    retrieve_document(context_id="ctx-1", filename="file.pdf", version=3, format="json")
    assert captured["json"]["context_id"] == "ctx-1"
    assert captured["json"]["filename"] == "file.pdf"
    assert captured["json"]["version"] == 3
    assert captured["json"]["format"] == "json"


def test_retrieve_document_invalid_format_defaults_text(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    payload = {}

    def fake_post(url, headers=None, json=None):
        payload.update(json or {})
        return DummyResponse(200, {"ok": True})

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    from examples.research.learning_agent import retrieve_document  # type: ignore

    retrieve_document(document_id="doc-1", format="bogus")
    assert payload["format"] == "text"



