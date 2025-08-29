from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Annotated
from langgraph.prebuilt import InjectedState

from deepagents.prompts import (
    WRITE_TODOS_DESCRIPTION,
    EDIT_DESCRIPTION,
    TOOL_DESCRIPTION,
    DELETE_DESCRIPTION,
)
from deepagents.state import Todo, DeepAgentState
import time


@tool(description=WRITE_TODOS_DESCRIPTION)
def write_todos(
    todos: list[Todo], tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(f"Updated todo list to {todos}", tool_call_id=tool_call_id)
            ],
        }
    )


def ls(state: Annotated[DeepAgentState, InjectedState]) -> list[str]:
    """List all files"""
    files = state.get("files", {})
    print(f"📁 LS DEBUG: Raw files state: {files}")
    
    # Filter out deleted files (files with None values)
    visible_files = [path for path, content in files.items() if content is not None]
    print(f"📁 LS DEBUG: Visible files after filtering: {visible_files}")
    
    return visible_files


@tool(description=TOOL_DESCRIPTION)
def read_file(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read file."""
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem or mock_filesystem.get(file_path) is None:
        return f"Error: File '{file_path}' not found"

    # Get file content
    content = mock_filesystem[file_path]

    # Handle empty file
    if not content or content.strip() == "":
        return "System reminder: File exists but has empty contents"

    # Split content into lines
    lines = content.splitlines()

    # Apply line offset and limit
    start_idx = offset
    end_idx = min(start_idx + limit, len(lines))

    # Handle case where offset is beyond file length
    if start_idx >= len(lines):
        return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

    # Format output with line numbers (cat -n format)
    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i]

        # Truncate lines longer than 2000 characters
        if len(line_content) > 2000:
            line_content = line_content[:2000]

        # Line numbers start at 1, so add 1 to the index
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")

    return "\n".join(result_lines)


def write_file(
    file_path: str,
    content: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Write to a file."""
    files = state.get("files", {})
    files[file_path] = content
    return Command(
        update={
            "files": files,
            "messages": [
                ToolMessage(f"Updated file {file_path}", tool_call_id=tool_call_id)
            ],
        }
    )


@tool(description=EDIT_DESCRIPTION)
def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    replace_all: bool = False,
) -> Command:
    """Write to a file."""
    mock_filesystem = state.get("files", {})
    # Check if file exists in mock filesystem (and is not deleted)
    if file_path not in mock_filesystem or mock_filesystem.get(file_path) is None:
        return f"Error: File '{file_path}' not found"

    # Get current file content
    content = mock_filesystem[file_path]

    # Check if old_string exists in the file
    if old_string not in content:
        return f"Error: String not found in file: '{old_string}'"

    # If not replace_all, check for uniqueness
    if not replace_all:
        occurrences = content.count(old_string)
        if occurrences > 1:
            return f"Error: String '{old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context."
        elif occurrences == 0:
            return f"Error: String not found in file: '{old_string}'"

    # Perform the replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacement_count = content.count(old_string)
        result_msg = f"Successfully replaced {replacement_count} instance(s) of the string in '{file_path}'"
    else:
        new_content = content.replace(
            old_string, new_string, 1
        )  # Replace only first occurrence
        result_msg = f"Successfully replaced string in '{file_path}'"

    # Update the mock filesystem
    mock_filesystem[file_path] = new_content
    return Command(
        update={
            "files": mock_filesystem,
            "messages": [ToolMessage(result_msg, tool_call_id=tool_call_id)],
        }
    )


@tool(description=DELETE_DESCRIPTION)
def delete_file(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Delete a file from the virtual file system."""
    mock_filesystem = state.get("files", {})
    
    # Debug: Print current state
    print(f"🗑️ DELETE DEBUG: Current VFS state has {len(mock_filesystem)} files: {list(mock_filesystem.keys())}")
    print(f"🗑️ DELETE DEBUG: Attempting to delete file: '{file_path}'")
    print(f"🗑️ DELETE DEBUG: File exists check: file_path in filesystem = {file_path in mock_filesystem}")
    if file_path in mock_filesystem:
        print(f"🗑️ DELETE DEBUG: File content is None = {mock_filesystem.get(file_path) is None}")
        print(f"🗑️ DELETE DEBUG: File content preview: {str(mock_filesystem.get(file_path))[:100]}...")
    
    # Check if file exists in mock filesystem (and is not already deleted)
    if file_path not in mock_filesystem or mock_filesystem.get(file_path) is None:
        print(f"🗑️ DELETE DEBUG: File '{file_path}' not found or already deleted")
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Error: File '{file_path}' not found", tool_call_id=tool_call_id)
                ]
            }
        )
    
    # Mark the file for deletion by setting it to None (deletion marker)
    # The file_reducer will filter out None values during state merge
    deletion_update = {file_path: None}
    
    print(f"🗑️ DELETE DEBUG: Creating deletion update: {deletion_update}")
    print(f"🗑️ DELETE DEBUG: Sending Command with files update containing deletion marker")
    
    return Command(
        update={
            "files": deletion_update,
            "messages": [
                ToolMessage(f"Successfully deleted file '{file_path}' (marked for deletion with None value)", tool_call_id=tool_call_id)
            ],
        }
    )


# =============================================================================
# Document Processing Tools
# =============================================================================

import os
import json
import datetime
import random
import string
import httpx
from supabase import create_client


@tool
def list_documents_with_context(
    state: Annotated[DeepAgentState, InjectedState],
    limit: int = 50, 
    offset: int = 0
) -> str:
    """List documents in the current conversation context.
    
    Args:
        state: Agent state containing contextId (injected automatically)
        limit: Maximum number of documents to return (default 50)
        offset: Number of documents to skip for pagination (default 0)
    """
    context_id = state.get("contextId")
    print(f"🔍 Backend DEBUG: contextId from state = {context_id}")
    
    if not context_id:
        print("⚠️ Backend WARNING: No contextId in state")
        return '{"error": "No contextId provided in agent state. Frontend must pass contextId.", "success": false}'
    
    # Lightweight per-process TTL cache to reduce duplicate calls across
    # rapid successive turns. Keyed by context and pagination.
    _cache = state.get("_ttl_cache", {})
    now = time.time()
    cache_key = ("list_docs", context_id, limit, offset)
    cached = _cache.get(cache_key)
    if cached and now - cached["ts"] < 60:
        return cached["value"]

    # Call the MCP list_documents tool directly with the context_id
    try:
        # Get Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return '{"error": "Supabase not configured", "success": false}'
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Query documents directly
        resp = supabase.table("da_documents").select(
            "id,filename,version,size_bytes,mime_type,source_mtime,source_path"
        ).eq("context_id", context_id).order("filename", desc=False).order("version", desc=True).limit(limit).offset(offset).execute()
        
        documents = resp.data or []
        result = {
            "success": True,
            "context_id": context_id,
            "documents": documents,
            "count": len(documents),
            "limit": limit,
            "offset": offset
        }
        
        print(f"✅ Backend SUCCESS: Found {len(documents)} documents for context_id = {context_id}")
        value = json.dumps(result, indent=2)
        _cache[cache_key] = {"ts": now, "value": value}
        return value
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Error querying documents: {str(e)}",
            "context_id": context_id
        }
        print(f"❌ Backend ERROR: {str(e)}")
        return json.dumps(error_result)


@tool  
def search_documents_with_context(
    state: Annotated[DeepAgentState, InjectedState],
    query: str,
    top_k: int = 5
) -> str:
    """Search processed documents within the current conversation context.
    
    Args:
        state: Agent state containing contextId (injected automatically)
        query: Natural language query to search for
        top_k: Maximum number of matches to return (default 5)
    """
    context_id = state.get("contextId")
    print(f"🔍 Backend DEBUG: search_documents contextId = {context_id}")
    
    if not context_id:
        return '{"error": "No contextId provided in agent state", "success": false}'
    
    # TTL cache keyed by (context_id, query, top_k) to avoid redundant searches
    _cache = state.get("_ttl_cache", {})
    now = time.time()
    cache_key = ("search_docs", context_id, query, top_k)
    cached = _cache.get(cache_key)
    if cached and now - cached["ts"] < 60:
        return cached["value"]

    # Call the existing search_documents function via edge function
    try:
        url = os.environ.get("SUPABASE_URL", "").rstrip("/") + "/functions/v1/rag_search"
        key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            return json.dumps({"success": False, "error": "Supabase configuration missing"})

        payload = {"query": query, "context_id": context_id, "top_k": top_k}
        
        import requests
        resp = requests.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload)
        resp.raise_for_status()
        result = resp.json()
        value = json.dumps({"success": True, "result": result})
        _cache[cache_key] = {"ts": now, "value": value}
        return value
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def convert_and_download_docx(
    state: Annotated[DeepAgentState, InjectedState],
    vfs_md_path: str,
    approved_docx_filename: str,
    include_toc: bool = False,
    reference_docx_path: str | None = None,
    resource_paths: list[str] | None = None,
) -> str:
    """Convert a VFS Markdown file to DOCX, upload to Supabase, and return a signed URL.

    Args:
        state: Agent state containing contextId (injected automatically)
        vfs_md_path: Path to the Markdown file in the Virtual File System
        approved_docx_filename: Desired filename for the generated .docx
        include_toc: Whether to include a table of contents in the DOCX
        reference_docx_path: Optional path to a reference .docx to control styles
        resource_paths: Optional list of directories for resolving images/resources

    Returns:
        JSON string with success status, storage details, and a temporary signed URL
    """
    import tempfile
    import traceback

    context_id = state.get("contextId")
    if not context_id:
        return json.dumps({"success": False, "error": "No contextId provided in agent state"})

    # Read Markdown from VFS
    mock_filesystem = state.get("files", {})
    if vfs_md_path not in mock_filesystem or mock_filesystem.get(vfs_md_path) is None:
        return json.dumps({"success": False, "error": f"File '{vfs_md_path}' not found in VFS"})

    md_content = mock_filesystem[vfs_md_path]
    if not isinstance(md_content, str) or md_content.strip() == "":
        return json.dumps({"success": False, "error": "Markdown file is empty or invalid"})

    # Ensure filename ends with .docx
    if not approved_docx_filename.lower().endswith(".docx"):
        approved_docx_filename = f"{approved_docx_filename}.docx"

    # Prepare Pandoc conversion
    extra_args: list[str] = []
    if include_toc:
        extra_args.append("--toc")
    if reference_docx_path:
        extra_args.extend(["--reference-doc", reference_docx_path])
    if resource_paths:
        # Join paths with OS separator for Pandoc's --resource-path
        extra_args.extend(["--resource-path", os.pathsep.join(resource_paths)])

    temp_docx_path = None
    try:
        import pypandoc

        # Attempt conversion; if pandoc is missing, download it and retry once
        def _convert_once() -> None:
            nonlocal temp_docx_path
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                temp_docx_path = tmp.name
            pypandoc.convert_text(
                md_content,
                to="docx",
                format="md",
                outputfile=temp_docx_path,
                extra_args=extra_args or None,
            )

        try:
            _convert_once()
        except Exception:
            # Try fetching pandoc binary and retry
            try:
                pypandoc.download_pandoc()
                _convert_once()
            except Exception as e2:
                err = f"Pandoc conversion failed: {type(e2).__name__}: {e2}"
                return json.dumps({"success": False, "error": err, "trace": traceback.format_exc()})

        # Read DOCX bytes
        if not temp_docx_path or not os.path.exists(temp_docx_path):
            return json.dumps({"success": False, "error": "DOCX not generated"})
        with open(temp_docx_path, "rb") as f:
            file_data = f.read()

        # Upload to Supabase Storage (generated-exports)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not all([supabase_url, supabase_service_key]):
            return json.dumps({"success": False, "error": "Supabase configuration missing"})

        supabase = create_client(supabase_url, supabase_service_key)

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        object_path = f"contexts/{context_id}/{timestamp}_{random_suffix}_{approved_docx_filename}"

        bucket = "generated-exports"
        upload_result = supabase.storage.from_(bucket).upload(
            object_path,
            file_data,
            file_options={
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            }
        )

        if hasattr(upload_result, 'error') and upload_result.error:
            return json.dumps({"success": False, "error": f"Storage upload failed: {upload_result.error}"})

        # Insert record
        insert_result = supabase.table("da_generated_exports").insert({
            "context_id": context_id,
            "filename": approved_docx_filename,
            "bucket": bucket,
            "object_path": object_path,
            "size_bytes": len(file_data),
        }).execute()

        if hasattr(insert_result, 'error') and insert_result.error:
            return json.dumps({"success": False, "error": f"Database insert failed: {insert_result.error}"})

        # Create signed URL (1 hour)
        try:
            signed = supabase.storage.from_(bucket).create_signed_url(object_path, 3600)
            signed_url = getattr(signed, 'signed_url', None) or getattr(signed, 'data', {}).get('signedURL') if isinstance(getattr(signed, 'data', None), dict) else None
            # Fallback: dict response shape
            if isinstance(signed, dict):
                signed_url = signed.get('signedURL') or signed.get('signed_url') or signed.get('data', {}).get('signedURL')
        except Exception as e:
            signed_url = None

        return json.dumps({
            "success": True,
            "bucket": bucket,
            "object_path": object_path,
            "filename": approved_docx_filename,
            "size_bytes": len(file_data),
            "signed_url": signed_url,
            "expires_in": 3600,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
    finally:
        try:
            if temp_docx_path and os.path.exists(temp_docx_path):
                os.remove(temp_docx_path)
        except Exception:
            pass


def retrieve_document(document_id: str = "", context_id: str = "", filename: str = "", version: int | None = None, format: str = "text"):
    """Retrieve a full document's content or original file via Edge Function.

    Provide either a document_id, or a (context_id, filename[, version]) tuple.

    Args:
        document_id: The document UUID to fetch (if known).
        context_id: Context UUID when resolving by filename.
        filename: Document filename to resolve (used with context_id).
        version: Optional version number; defaults to latest when omitted.
        format: One of 'text' (text_content), 'json' (raw_json), or 'original' (signed URL).

    Returns:
        JSON payload containing the requested representation of the document.
    """
    url = os.environ.get("SUPABASE_URL", "").rstrip("/") + "/functions/v1/retrieve_document"
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    # Validate inputs
    if not document_id and not (context_id and filename):
        raise ValueError("Either document_id or (context_id, filename) must be provided")

    # Validate format
    if format not in ["text", "json", "original"]:
        format = "text"

    payload = {}
    if document_id:
        payload["document_id"] = document_id
    else:
        payload["context_id"] = context_id
        payload["filename"] = filename
        if version is not None:
            payload["version"] = version

    payload["format"] = format

    import requests
    resp = requests.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload)
    resp.raise_for_status()
    return resp.json()


@tool
def process_agent_document(
    state: Annotated[DeepAgentState, InjectedState],
    vfs_file_path: str,
    approved_filename: str,
    content_type: str = "text/plain"
) -> str:
    """Process an approved document from VFS through Supabase ingest pipeline.
    
    This tool uploads agent-created documents to Supabase storage and triggers
    the same processing pipeline used for user uploads. The document becomes
    searchable and retrievable within the current conversation context.
    
    Args:
        state: Agent state containing contextId (injected automatically)
        vfs_file_path: Path to the file in the Virtual File System
        approved_filename: The filename to use when storing the document
        content_type: MIME type of the content (default: text/plain)
        
    Returns:
        JSON string with processing result and status
    """
    context_id = state.get("contextId")
    print(f"🔍 Backend DEBUG: process_agent_document contextId = {context_id}")
    
    if not context_id:
        return json.dumps({"success": False, "error": "No contextId provided in agent state"})
    
    try:
        # Read content from VFS using the built-in read_file function
        # The VFS read_file function requires state parameter
        mock_filesystem = state.get("files", {})
        if vfs_file_path not in mock_filesystem or mock_filesystem.get(vfs_file_path) is None:
            return json.dumps({"success": False, "error": f"File '{vfs_file_path}' not found in VFS"})
        
        vfs_content = mock_filesystem[vfs_file_path]
        if not vfs_content:
            return json.dumps({"success": False, "error": f"Could not read file from VFS: {vfs_file_path}"})
        
        # Convert content to bytes
        if isinstance(vfs_content, str):
            file_data = vfs_content.encode('utf-8')
        else:
            file_data = vfs_content
            
        # Generate unique object path (same pattern as frontend)
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        object_path = f"contexts/{context_id}/{timestamp}_{random_suffix}_{approved_filename}"
        
        # Get Supabase configuration
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not all([supabase_url, supabase_service_key]):
            return json.dumps({"success": False, "error": "Supabase configuration missing"})
        
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_service_key)
        
        # Upload to Supabase storage
        upload_result = supabase.storage.from_("context-uploads").upload(
            object_path, 
            file_data,
            file_options={"content-type": content_type}
        )
        
        if hasattr(upload_result, 'error') and upload_result.error:
            return json.dumps({"success": False, "error": f"Storage upload failed: {upload_result.error}"})
            
        # Insert upload record
        upload_record = supabase.table("da_context_uploads").insert({
            "context_id": context_id,
            "bucket": "context-uploads",
            "object_path": object_path,
            "filename": approved_filename,
            "size_bytes": len(file_data),
            "status": "uploaded"
        }).execute()
        
        if hasattr(upload_record, 'error') and upload_record.error:
            return json.dumps({"success": False, "error": f"Database insert failed: {upload_record.error}"})
            
        upload_id = upload_record.data[0]["id"]
        
        # Trigger processing via edge function (same as user uploads)
        edge_function_url = f"{supabase_url}/functions/v1/ingest_upload"
        
        with httpx.Client() as client:
            response = client.post(
                edge_function_url,
                headers={
                    "Authorization": f"Bearer {supabase_service_key}",
                    "apikey": supabase_service_key,
                    "Content-Type": "application/json"
                },
                json={
                    "context_id": context_id,
                    "bucket": "context-uploads",
                    "object_path": object_path,
                    "filename": approved_filename,
                    "size_bytes": len(file_data),
                    "upload_id": upload_id
                },
                timeout=30
            )
            
        return json.dumps({
            "success": True,
            "upload_id": upload_id,
            "object_path": object_path,
            "filename": approved_filename,
            "size_bytes": len(file_data),
            "status": "processing",
            "message": f"Agent document '{approved_filename}' uploaded and processing started"
        })
        
    except Exception as e:
        print(f"❌ Backend ERROR in process_agent_document: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})