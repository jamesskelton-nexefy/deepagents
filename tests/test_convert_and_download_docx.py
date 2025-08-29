import json
import os
import sys


class _StubPandoc:
    def download_pandoc(self):
        return None

    def convert_text(self, md_content, to, format, outputfile, extra_args=None):
        # Write minimal DOCX-like bytes to the output file path
        with open(outputfile, "wb") as f:
            f.write(b"PK\x03\x04stub-docx-content")


class _StubStorageBucket:
    def __init__(self):
        self.uploads = {}

    def upload(self, object_path, file_data, file_options=None):
        # Record the upload and return a simple object without error
        self.uploads[object_path] = {
            "data": file_data,
            "options": file_options or {},
        }

        class _Resp:
            error = None

        return _Resp()

    def create_signed_url(self, object_path, expires_in_seconds):
        # Return a dict similar to the Python client shape
        return {"signedURL": f"https://example.com/{object_path}?sig=abc&exp={expires_in_seconds}"}


class _StubStorage:
    def __init__(self):
        self._bucket = _StubStorageBucket()

    def from_(self, bucket):
        return self._bucket


class _StubQueryResp:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error


class _StubTableBuilder:
    def __init__(self, table_name):
        self._table = table_name

    def insert(self, row):
        # Simulate .execute() by returning a stub response with data
        class _Exec:
            def execute(self_inner):
                return _StubQueryResp(data=[{"id": "stub-id"}], error=None)

        return _Exec()


class _StubSupabaseClient:
    def __init__(self):
        self.storage = _StubStorage()

    def table(self, table_name):
        return _StubTableBuilder(table_name)


def _stub_create_client(url, key):
    return _StubSupabaseClient()


def test_convert_and_download_docx_happy_path(monkeypatch):
    # Inject stub pypandoc before importing tool function
    sys.modules["pypandoc"] = _StubPandoc()

    # Import after stubbing
    from deepagents.tools import convert_and_download_docx, create_client

    # Patch Supabase client factory
    monkeypatch.setattr("deepagents.tools.create_client", _stub_create_client, raising=True)

    # Minimal state with a Markdown file in VFS and a contextId
    state = {
        "files": {"/work/doc.md": "# Title\n\nSome text with **bold**."},
        "contextId": "00000000-0000-0000-0000-000000000001",
    }

    result_json = convert_and_download_docx(
        state=state,
        vfs_md_path="/work/doc.md",
        approved_docx_filename="export.docx",
        include_toc=True,
    )
    result = json.loads(result_json)

    assert result.get("success") is True
    assert result.get("bucket") == "generated-exports"
    assert result.get("filename") == "export.docx"
    assert result.get("size_bytes", 0) > 0
    assert isinstance(result.get("signed_url"), str) and len(result["signed_url"]) > 0


