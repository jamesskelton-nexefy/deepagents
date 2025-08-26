import os
import io
import json
import time
import hashlib
import mimetypes
import asyncio
from typing import AsyncIterator, Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from supabase import create_client, Client
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared
from mcp.server.fastmcp import FastMCP, Context


@dataclass
class AppContext:
    client: UnstructuredClient
    supabase: Optional[Client]


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manages the Unstructured API client lifecycle."""
    api_key = os.getenv("UNSTRUCTURED_API_KEY")
    if not api_key:
        raise ValueError("UNSTRUCTURED_API_KEY environment variable is required")

    client = UnstructuredClient(api_key_auth=api_key)

    # Initialize Supabase client if env is present
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    supabase_client = None
    if supabase_url and supabase_key:
        try:
            supabase_client = create_client(supabase_url, supabase_key)
        except Exception as _e:
            supabase_client = None
    # Expose globally for background workers
    global _APP_CONTEXT
    _APP_CONTEXT = AppContext(client=client, supabase=supabase_client)
    try:
        # Start global realtime listener and reconciliation in background if Supabase available
        if _APP_CONTEXT.supabase is not None:
            bucket = os.getenv("SUPABASE_UPLOADS_BUCKET", "context-uploads")
            # Subscribe in background thread to avoid blocking
            asyncio.create_task(asyncio.to_thread(_subscribe_global_uploads, _APP_CONTEXT.supabase, bucket))
            # Start reconcile loop
            asyncio.create_task(_reconcile_loop(_APP_CONTEXT.supabase, bucket))

        yield _APP_CONTEXT
    finally:
        # No cleanup needed for the API client.
        pass


# Globals for realtime processing
_APP_CONTEXT: Optional[AppContext] = None
_UPLOAD_QUEUES: Dict[str, asyncio.Queue] = {}
_LISTENER_TASKS: Dict[str, asyncio.Task] = {}
_WORKER_TASKS: Dict[str, asyncio.Task] = {}


def _ensure_context_worker(context_id: str, bucket: str) -> None:
    if context_id not in _UPLOAD_QUEUES:
        _UPLOAD_QUEUES[context_id] = asyncio.Queue()
        _WORKER_TASKS[context_id] = asyncio.create_task(_worker_loop(context_id, bucket))


def _on_any_upload_event(context_id: str, record: Dict[str, Any], bucket: str) -> None:
    # Only act on uploaded status
    if record.get("status") != "uploaded":
        return
    _ensure_context_worker(context_id, bucket)
    # Enqueue safely from callback
    asyncio.get_event_loop().call_soon_threadsafe(_UPLOAD_QUEUES[context_id].put_nowait, record)


def _subscribe_global_uploads(supabase_client: Client, bucket: str) -> None:
    channel = supabase_client.realtime.channel("ctx-global-uploads")

    def _handler(payload: Dict[str, Any]):
        try:
            new = payload.get("new") or payload.get("record") or {}
            context_id = new.get("context_id")
            if not context_id:
                return
            _on_any_upload_event(context_id, new, bucket)
        except Exception:
            pass

    # INSERT and UPDATE events on uploads table
    for evt in ("INSERT", "UPDATE"):
        channel.on(
            "postgres_changes",
            {
                "event": evt,
                "schema": "public",
                "table": "da_context_uploads",
            },
            _handler,
        )
    channel.subscribe()


async def _reconcile_once(supabase_client: Client, bucket: str) -> int:
    try:
        resp = await asyncio.to_thread(
            lambda: supabase_client.table("da_context_uploads")
            .select("id,context_id,bucket,object_path,filename,status")
            .eq("status", "uploaded")
            .limit(500)
            .execute()
        )
        rows = resp.data or []
        for r in rows:
            ctx_id = r.get("context_id")
            if not ctx_id:
                continue
            _ensure_context_worker(ctx_id, bucket)
            await _UPLOAD_QUEUES[ctx_id].put(r)
        return len(rows)
    except Exception:
        return 0


async def _reconcile_loop(supabase_client: Client, bucket: str, interval_sec: int = 180) -> None:
    # Initial sweep
    await _reconcile_once(supabase_client, bucket)
    while True:
        await asyncio.sleep(interval_sec)
        await _reconcile_once(supabase_client, bucket)


# Create the MCP server instance.
mcp = FastMCP(
    "unstructured-partition-mcp",
    lifespan=app_lifespan,
    dependencies=[
        "unstructured-client",
        "python-dotenv",
        "supabase",
        "openai",
    ],
)

# Specify the absolute path to the local directory to store processed files.
PROCESSED_FILES_FOLDER = os.getenv("UNSTRUCTURED_OUTPUT_DIR", "/tmp/unstructured_output")


def load_environment_variables() -> None:
    """
    Load environment variables from .env file.
    Raises an error if critical environment variables are missing.
    """
    # Try loading from current working directory; if not present, that's fine because
    # we also accept env vars passed in via the process environment.
    load_dotenv()

    required_vars = [
        "UNSTRUCTURED_API_KEY",
    ]

    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")


def _compute_file_fingerprint(path: str) -> dict:
    stat = os.stat(path)
    size_bytes = stat.st_size
    mtime = stat.st_mtime
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    sha256 = hasher.hexdigest()
    filename = os.path.basename(path)
    mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return {
        "sha256": sha256,
        "size_bytes": size_bytes,
        "mtime": mtime,
        "filename": filename,
        "mime_type": mime_type,
    }


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = max(end - overlap, start + 1)
    return chunks


async def _embed_chunks(chunks: List[str]) -> Optional[List[List[float]]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI()
        resp = await asyncio.to_thread(
            client.embeddings.create,
            model="text-embedding-3-small",
            input=chunks,
        )
        vectors = [d.embedding for d in resp.data]
        return vectors
    except Exception:
        return None


def json_to_text(file_path: str) -> str:
    with open(file_path, "r") as file:
        elements = json.load(file)

    doc_texts: list[str] = []

    for element in elements:
        text = element.get("text", "").strip()
        element_type = element.get("type", "")
        metadata = element.get("metadata", {})

        if element_type == "Title":
            doc_texts.append(f"<h1> {text}</h1><br>")
        elif element_type == "Header":
            doc_texts.append(f"<h2> {text}</h2><br/>")
        elif element_type == "NarrativeText" or element_type == "UncategorizedText":
            doc_texts.append(f"<p>{text}</p>")
        elif element_type == "ListItem":
            doc_texts.append(f"<li>{text}</li>")
        elif element_type == "PageNumber":
            doc_texts.append(f"Page number: {text}")
        elif element_type == "Table":
            table_html = metadata.get("text_as_html", "")
            doc_texts.append(table_html)  # Keep the table as HTML.
        else:
            doc_texts.append(text)

    return " ".join(doc_texts)


@mcp.tool()
async def process_document(ctx: Context, filepath: str, context_id: Optional[str] = None) -> str:
    """
    Sends the document to Unstructured for processing.
    Returns the processed contents of the document

    Args:
        filepath: The local path to the document.
    """

    filepath = os.path.abspath(filepath)
    logs: list[str] = []
    def _log(msg: str) -> None:
        try:
            logs.append(msg)
        except Exception:
            pass

    # Use background threads for blocking filesystem checks
    file_exists = await asyncio.to_thread(os.path.isfile, filepath)
    if not file_exists:
        _log(f"File does not exist: {filepath}")
        return "DEBUG LOG:\n" + "\n".join(logs)

    # Check whether Unstructured supports the file's extension.
    _, ext = os.path.splitext(filepath)
    supported_extensions = {
        ".abw",
        ".bmp",
        ".csv",
        ".cwk",
        ".dbf",
        ".dif",
        ".doc",
        ".docm",
        ".docx",
        ".dot",
        ".dotm",
        ".eml",
        ".epub",
        ".et",
        ".eth",
        ".fods",
        ".gif",
        ".heic",
        ".htm",
        ".html",
        ".hwp",
        ".jpeg",
        ".jpg",
        ".md",
        ".mcw",
        ".mw",
        ".odt",
        ".org",
        ".p7s",
        ".pages",
        ".pbd",
        ".pdf",
        ".png",
        ".pot",
        ".potm",
        ".ppt",
        ".pptm",
        ".pptx",
        ".prn",
        ".rst",
        ".rtf",
        ".sdp",
        ".sgl",
        ".svg",
        ".sxg",
        ".tiff",
        ".txt",
        ".tsv",
        ".uof",
        ".uos1",
        ".uos2",
        ".web",
        ".webp",
        ".wk2",
        ".xls",
        ".xlsb",
        ".xlsm",
        ".xlsx",
        ".xlw",
        ".xml",
        ".zabw",
    }

    if ext.lower() not in supported_extensions:
        _log(f"Unsupported extension: {ext}")
        return "DEBUG LOG:\n" + "\n".join(logs)

    client = ctx.request_context.lifespan_context.client
    supabase_client = ctx.request_context.lifespan_context.supabase
    _log(f"Supabase configured: {bool(supabase_client)}")
    file_basename = os.path.basename(filepath)

    # Ensure output directory exists (blocking)
    await asyncio.to_thread(os.makedirs, PROCESSED_FILES_FOLDER, exist_ok=True)

    # Check Supabase cache by sha256
    fp = await asyncio.to_thread(_compute_file_fingerprint, filepath)
    _log(f"Fingerprint computed: sha256={fp['sha256'][:12]}... size={fp['size_bytes']} mime={fp['mime_type']}")
    if supabase_client is not None:
        try:
            # For cache: if exact sha exists anywhere, reuse text regardless of context
            data = await asyncio.to_thread(
                lambda: supabase_client.table("da_documents").select("id,text_content").eq("sha256", fp["sha256"]).limit(1).maybe_single().execute()
            )
            if data and getattr(data, "data", None):
                row = data.data
                cached_text = row.get("text_content")
                if cached_text:
                    _log("Cache hit in Supabase (da_documents) -> returning cached text")
                    return "DEBUG LOG:\n" + "\n".join(logs) + "\n\n" + cached_text
            _log("Cache miss in Supabase (da_documents)")
        except Exception as e:
            _log(f"Supabase cache check error: {type(e).__name__}: {e}")

    # Build and execute the partition request in a background thread using a real BufferedReader
    def _partition(client: UnstructuredClient, path: str):
        with open(path, "rb") as f:
            req = operations.PartitionRequest(
                partition_parameters=shared.PartitionParameters(
                    files=shared.Files(
                        content=f,
                        file_name=path,
                    ),
                    strategy=shared.Strategy.AUTO,
                ),
            )
            return client.general.partition(request=req)

    try:
        # Call the Unstructured API off the event loop
        res = await asyncio.to_thread(_partition, client, filepath)
        element_dicts = [element for element in res.elements]
        _log(f"Unstructured returned {len(element_dicts)} elements")

        # Persist elements to JSON (off loop)
        json_elements = json.dumps(element_dicts, indent=2)
        output_json_file_path = os.path.join(
            PROCESSED_FILES_FOLDER, f"{file_basename}.json"
        )

        def _write_text(path: str, text: str) -> None:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

        await asyncio.to_thread(_write_text, output_json_file_path, json_elements)
        _log(f"Wrote JSON to {output_json_file_path}")

        # Convert elements to displayable text without re-reading from disk
        doc_texts: list[str] = []
        for element in element_dicts:
            text = element.get("text", "").strip()
            element_type = element.get("type", "")
            metadata = element.get("metadata", {})

            if element_type == "Title":
                doc_texts.append(f"<h1> {text}</h1><br>")
            elif element_type == "Header":
                doc_texts.append(f"<h2> {text}</h2><br/>")
            elif element_type == "NarrativeText" or element_type == "UncategorizedText":
                doc_texts.append(f"<p>{text}</p>")
            elif element_type == "ListItem":
                doc_texts.append(f"<li>{text}</li>")
            elif element_type == "PageNumber":
                doc_texts.append(f"Page number: {text}")
            elif element_type == "Table":
                table_html = metadata.get("text_as_html", "")
                doc_texts.append(table_html)
            else:
                doc_texts.append(text)

        text_content = " ".join(doc_texts)

        # Upsert into Supabase (documents + chunks + embeddings)
        if supabase_client is not None:
            try:
                # Insert document
                insert_doc = {
                    "source_path": filepath,
                    "source_mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(fp["mtime"])),
                    "sha256": fp["sha256"],
                    "filename": fp["filename"],
                    "size_bytes": fp["size_bytes"],
                    "mime_type": fp["mime_type"],
                    "text_content": text_content,
                    "raw_json": element_dicts,
                    "context_id": context_id,
                }
                # Determine version for (context_id, filename)
                version_num = 1
                if context_id:
                    try:
                        ver_resp = await asyncio.to_thread(
                            lambda: supabase_client.table("da_documents").select("version,sha256").eq("context_id", context_id).eq("filename", fp["filename"]).order("version", desc=True).limit(1).execute()
                        )
                        rows = ver_resp.data or []
                        if rows:
                            last = rows[0]
                            if last.get("sha256") != fp["sha256"]:
                                version_num = int(last.get("version", 1)) + 1
                            else:
                                version_num = int(last.get("version", 1))
                    except Exception as ve:
                        _log(f"Version query error: {type(ve).__name__}: {ve}")
                insert_doc["version"] = version_num

                # Upsert by sha256 and then fetch id
                await asyncio.to_thread(
                    lambda: supabase_client.table("da_documents").upsert(insert_doc, on_conflict="sha256").execute()
                )
                fetch_resp = await asyncio.to_thread(
                    lambda: supabase_client.table("da_documents").select("id").eq("sha256", fp["sha256"]).maybe_single().execute()
                )
                document_id = fetch_resp.data.get("id") if (fetch_resp and getattr(fetch_resp, "data", None)) else None
                _log(f"Upserted document; document_id={document_id}")

                # Update latest alias per (context, filename)
                if context_id and document_id:
                    try:
                        await asyncio.to_thread(
                            lambda: supabase_client.table("da_context_file_aliases").upsert({
                                "context_id": context_id,
                                "filename": fp["filename"],
                                "latest_document_id": document_id,
                            }, on_conflict="context_id,filename").execute()
                        )
                    except Exception as ae:
                        _log(f"Alias upsert error: {type(ae).__name__}: {ae}")

                # Chunk and embed
                chunks = await asyncio.to_thread(_chunk_text, text_content)
                _log(f"Chunked into {len(chunks)} chunks")
                embeddings = await _embed_chunks(chunks)  # may be None
                _log(f"Embeddings created: {embeddings is not None}")

                # Prepare rows
                rows = []
                for i, chunk in enumerate(chunks):
                    row = {
                        "document_id": document_id,
                        "chunk_index": i,
                        "content": chunk,
                        "context_id": context_id,
                    }
                    if embeddings is not None and i < len(embeddings):
                        row["embedding"] = embeddings[i]
                    rows.append(row)

                # Insert rows in batches to avoid payload limits
                batch_size = 100
                total_inserted = 0
                for i in range(0, len(rows), batch_size):
                    batch = rows[i : i + batch_size]
                    await asyncio.to_thread(
                        lambda b=batch: supabase_client.table("da_document_chunks").insert(b).execute()
                    )
                    total_inserted += len(batch)
                _log(f"Inserted {total_inserted} chunks into Supabase")
            except Exception as pe:
                _log(f"Supabase persistence error: {type(pe).__name__}: {pe}")

        return "DEBUG LOG:\n" + "\n".join(logs) + "\n\n" + text_content
    except Exception as e:
        _log(f"Processing error: {type(e).__name__}: {e}")
        return "DEBUG LOG:\n" + "\n".join(logs)


@mcp.tool()
async def search_documents(ctx: Context, query: str, top_k: int = 5) -> str:
    """Semantic search over processed document chunks stored in Supabase."""
    supabase_client = ctx.request_context.lifespan_context.supabase
    if supabase_client is None:
        return "Supabase is not configured."

    # Embed query
    vectors = await _embed_chunks([query])
    if not vectors:
        return "Embeddings not available. Set OPENAI_API_KEY to enable search."
    query_emb = vectors[0]

    try:
        # RPC call to SQL function
        resp = await asyncio.to_thread(
            lambda: supabase_client.rpc(
                "da_search_chunks",
                {"query_embedding": query_emb, "match_count": top_k},
            ).execute()
        )
        rows = (resp.data or []) if hasattr(resp, "data") else []
        lines = []
        for r in rows:
            sim = r.get("similarity")
            lines.append(f"doc={r.get('document_id')} idx={r.get('chunk_index')} sim={sim:.3f}: {r.get('content')[:300]}")
        return "\n".join(lines) if lines else "No matches."
    except Exception as e:
        return f"Search error: {e}"


async def _download_to_temp(supabase_client: Client, bucket: str, object_path: str, filename: str) -> str:
    # Download bytes and write to a temp path
    data = await asyncio.to_thread(lambda: supabase_client.storage.from_(bucket).download(object_path))
    temp_name = f"ingest_{int(time.time())}_{filename}"
    temp_path = os.path.join(PROCESSED_FILES_FOLDER, temp_name)
    await asyncio.to_thread(os.makedirs, PROCESSED_FILES_FOLDER, exist_ok=True)
    def _write_bytes(path: str, b: bytes) -> None:
        with open(path, "wb") as f:
            f.write(b)
    await asyncio.to_thread(_write_bytes, temp_path, data)
    return temp_path


async def _process_and_persist(filepath: str, context_id: Optional[str]) -> tuple[bool, str, Optional[str]]:
    """Run Unstructured partition and persist to Supabase using global context.
    Returns (ok, log, document_id)
    """
    logs: list[str] = []
    def _log(m: str):
        logs.append(m)
    if _APP_CONTEXT is None or _APP_CONTEXT.supabase is None:
        _log("Supabase not configured in background context")
        return False, "\n".join(logs), None
    client = _APP_CONTEXT.client
    supabase_client = _APP_CONTEXT.supabase
    # Reuse core of process_document
    try:
        # Partition
        req = operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=shared.Files(content=open(filepath, "rb"), file_name=filepath),
                strategy=shared.Strategy.AUTO,
            ),
        )
        res = await asyncio.to_thread(lambda: client.general.partition(request=req))
        element_dicts = [e for e in res.elements]
        _log(f"Unstructured elements: {len(element_dicts)}")

        # Text render
        doc_texts: list[str] = []
        for element in element_dicts:
            text = element.get("text", "").strip()
            element_type = element.get("type", "")
            metadata = element.get("metadata", {})
            if element_type == "Title":
                doc_texts.append(f"<h1> {text}</h1><br>")
            elif element_type == "Header":
                doc_texts.append(f"<h2> {text}</h2><br/>")
            elif element_type in ("NarrativeText", "UncategorizedText"):
                doc_texts.append(f"<p>{text}</p>")
            elif element_type == "ListItem":
                doc_texts.append(f"<li>{text}</li>")
            elif element_type == "PageNumber":
                doc_texts.append(f"Page number: {text}")
            elif element_type == "Table":
                doc_texts.append(metadata.get("text_as_html", ""))
            else:
                doc_texts.append(text)
        text_content = " ".join(doc_texts)

        # Fingerprint and upsert
        fp = await asyncio.to_thread(_compute_file_fingerprint, filepath)
        insert_doc = {
            "source_path": filepath,
            "source_mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(fp["mtime"])),
            "sha256": fp["sha256"],
            "filename": fp["filename"],
            "size_bytes": fp["size_bytes"],
            "mime_type": fp["mime_type"],
            "text_content": text_content,
            "raw_json": element_dicts,
            "context_id": context_id,
        }
        # Version calculation
        version_num = 1
        if context_id:
            try:
                ver_resp = await asyncio.to_thread(
                    lambda: supabase_client.table("da_documents").select("version,sha256").eq("context_id", context_id).eq("filename", fp["filename"]).order("version", desc=True).limit(1).execute()
                )
                rows = ver_resp.data or []
                if rows:
                    last = rows[0]
                    version_num = int(last.get("version", 1)) + (1 if last.get("sha256") != fp["sha256"] else 0)
            except Exception as ve:
                _log(f"Version query error: {type(ve).__name__}: {ve}")
        insert_doc["version"] = version_num

        await asyncio.to_thread(lambda: supabase_client.table("da_documents").upsert(insert_doc, on_conflict="sha256").execute())
        fetch_resp = await asyncio.to_thread(lambda: supabase_client.table("da_documents").select("id").eq("sha256", fp["sha256"]).maybe_single().execute())
        document_id = fetch_resp.data.get("id") if (fetch_resp and getattr(fetch_resp, "data", None)) else None
        _log(f"Upserted document_id={document_id}")

        # Alias
        if context_id and document_id:
            try:
                await asyncio.to_thread(lambda: supabase_client.table("da_context_file_aliases").upsert({
                    "context_id": context_id,
                    "filename": fp["filename"],
                    "latest_document_id": document_id,
                }, on_conflict="context_id,filename").execute())
            except Exception as ae:
                _log(f"Alias upsert error: {type(ae).__name__}: {ae}")

        # Chunk + embed
        chunks = await asyncio.to_thread(_chunk_text, text_content)
        embeddings = await _embed_chunks(chunks)
        rows = []
        for i, chunk in enumerate(chunks):
            row = {"document_id": document_id, "chunk_index": i, "content": chunk, "context_id": context_id}
            if embeddings is not None and i < len(embeddings):
                row["embedding"] = embeddings[i]
            rows.append(row)
        for i in range(0, len(rows), 100):
            batch = rows[i:i+100]
            await asyncio.to_thread(lambda b=batch: supabase_client.table("da_document_chunks").insert(b).execute())
        _log(f"Inserted {len(rows)} chunks")
        return True, "\n".join(logs), document_id
    except Exception as e:
        _log(f"Background processing error: {type(e).__name__}: {e}")
        return False, "\n".join(logs), None


async def _worker_loop(context_id: str, bucket: str):
    q = _UPLOAD_QUEUES[context_id]
    supabase_client = _APP_CONTEXT.supabase if _APP_CONTEXT else None
    while True:
        item: Dict[str, Any] = await q.get()
        try:
            upload_id = item.get("id")
            object_path = item.get("object_path")
            filename = item.get("filename")
            # Mark processing
            if supabase_client:
                await asyncio.to_thread(lambda: supabase_client.table("da_context_uploads").update({"status": "processing", "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}).eq("id", upload_id).execute())
            # Download
            temp_path = await _download_to_temp(supabase_client, bucket, object_path, filename)
            # Process
            ok, log, doc_id = await _process_and_persist(temp_path, context_id)
            # Update status
            if supabase_client:
                if ok:
                    await asyncio.to_thread(lambda: supabase_client.table("da_context_uploads").update({"status": "processed", "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "document_id": doc_id}).eq("id", upload_id).execute())
                else:
                    await asyncio.to_thread(lambda: supabase_client.table("da_context_uploads").update({"status": "failed", "error": log}).eq("id", upload_id).execute())
        except Exception as e:
            # Best-effort error reporting
            if _APP_CONTEXT and _APP_CONTEXT.supabase and item.get("id"):
                await asyncio.to_thread(lambda: _APP_CONTEXT.supabase.table("da_context_uploads").update({"status": "failed", "error": f"worker error: {type(e).__name__}: {e}"}).eq("id", item["id"]).execute())
        finally:
            q.task_done()


@mcp.tool()
async def start_realtime_context_uploads_listener(ctx: Context, context_id: str) -> str:
    """Start a realtime listener for new uploads in the given context and process immediately."""
    if _APP_CONTEXT is None or _APP_CONTEXT.supabase is None:
        return "Supabase is not configured."
    supabase_client = _APP_CONTEXT.supabase
    bucket = os.getenv("SUPABASE_UPLOADS_BUCKET", "context-uploads")

    # Create queue and worker if not exists
    if context_id not in _UPLOAD_QUEUES:
        _UPLOAD_QUEUES[context_id] = asyncio.Queue()
        _WORKER_TASKS[context_id] = asyncio.create_task(_worker_loop(context_id, bucket))

    # Set up realtime subscription once per context
    if context_id in _LISTENER_TASKS:
        return f"Listener already running for context {context_id}"

    def _on_insert(payload: Dict[str, Any]):
        try:
            new = payload.get("new") or payload.get("record") or {}
            if not new:
                return
            if new.get("context_id") != context_id:
                return
            if new.get("status") != "uploaded":
                return
            # Enqueue
            asyncio.get_event_loop().call_soon_threadsafe(_UPLOAD_QUEUES[context_id].put_nowait, new)
        except Exception:
            pass

    def _subscribe():
        channel = supabase_client.realtime.channel(f"ctx-{context_id}")
        channel.on(
            "postgres_changes",
            {
                "event": "INSERT",
                "schema": "public",
                "table": "da_context_uploads",
                "filter": f"context_id=eq.{context_id}",
            },
            _on_insert,
        )
        channel.subscribe()

    # Run subscription in background thread to avoid blocking event loop
    _LISTENER_TASKS[context_id] = asyncio.create_task(asyncio.to_thread(_subscribe))
    return f"Started realtime listener for context {context_id} on bucket {bucket}"

if __name__ == "__main__":
    load_environment_variables()
    # Initialize and run the server.
    mcp.run(transport="stdio")


