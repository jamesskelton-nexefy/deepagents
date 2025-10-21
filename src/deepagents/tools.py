from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langchain.tools.tool_node import InjectedState
from typing import Annotated, Union
from deepagents.state import Todo, FilesystemState
from deepagents.prompts import (
    WRITE_TODOS_TOOL_DESCRIPTION,
    LIST_FILES_TOOL_DESCRIPTION,
    READ_FILE_TOOL_DESCRIPTION,
    WRITE_FILE_TOOL_DESCRIPTION,
    EDIT_FILE_TOOL_DESCRIPTION,
    REQUEST_DOCUMENT_UPLOAD_TOOL_DESCRIPTION,
    RETRIEVE_CONTEXT_TOOL_DESCRIPTION,
    INDEX_DOCUMENT_TOOL_DESCRIPTION,
)
from deepagents.vector_store import get_vector_store_manager


@tool(description=WRITE_TODOS_TOOL_DESCRIPTION)
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


@tool(description=LIST_FILES_TOOL_DESCRIPTION)
def ls(state: Annotated[FilesystemState, InjectedState]) -> list[str]:
    """List all files"""
    return list(state.get("files", {}).keys())


@tool(description=READ_FILE_TOOL_DESCRIPTION)
def read_file(
    file_path: str,
    state: Annotated[FilesystemState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
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


@tool(description=WRITE_FILE_TOOL_DESCRIPTION)
def write_file(
    file_path: str,
    content: str,
    state: Annotated[FilesystemState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
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


@tool(description=EDIT_FILE_TOOL_DESCRIPTION)
def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    state: Annotated[FilesystemState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    replace_all: bool = False,
) -> Union[Command, str]:
    """Write to a file."""
    mock_filesystem = state.get("files", {})
    # Check if file exists in mock filesystem
    if file_path not in mock_filesystem:
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


@tool(description=REQUEST_DOCUMENT_UPLOAD_TOOL_DESCRIPTION)
def request_document_upload(
    prompt: str = "Please upload a document",
    accepted_formats: list[str] = ["pdf", "docx", "pptx"],
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Command:
    """Request the user to upload a document.
    
    Args:
        prompt: Message to display to the user explaining what document to upload
        accepted_formats: List of accepted file formats (pdf, docx, pptx)
        tool_call_id: Injected tool call ID
    
    Returns:
        Command with message indicating upload request
    """
    formats_str = ", ".join(accepted_formats)
    result_message = f"UPLOAD_REQUEST: {prompt} (Accepted formats: {formats_str})"
    
    return Command(
        update={
            "messages": [
                ToolMessage(result_message, tool_call_id=tool_call_id)
            ],
        }
    )


@tool(description=INDEX_DOCUMENT_TOOL_DESCRIPTION)
def index_document(
    file_path: str,
    config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Index an uploaded document for retrieval.
    
    This tool loads a document, chunks it, and adds it to the vector store
    so it can be searched with retrieve_context.
    
    Args:
        file_path: Absolute path to the uploaded document
        config: LangGraph config containing thread_id
        tool_call_id: Injected tool call ID
    
    Returns:
        Command with success message
    """
    import sys
    from pathlib import Path
    from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredPowerPointLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    try:
        # Get thread_id from config
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return Command(
                update={
                    "messages": [
                        ToolMessage("Error: No thread_id found. Cannot index document.", tool_call_id=tool_call_id)
                    ]
                }
            )
        
        print(f"DEBUG index_document: Indexing {file_path} for thread {thread_id}", file=sys.stderr)
        
        # Determine file type
        file_extension = Path(file_path).suffix.lstrip(".").lower()
        
        # Load document based on type
        if file_extension == "pdf":
            loader = PyPDFLoader(file_path)
        elif file_extension == "docx":
            loader = Docx2txtLoader(file_path)
        elif file_extension == "pptx":
            loader = UnstructuredPowerPointLoader(file_path)
        else:
            return Command(
                update={
                    "messages": [
                        ToolMessage(f"Error: Unsupported file type: {file_extension}", tool_call_id=tool_call_id)
                    ]
                }
            )
        
        # Load and split documents
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)
        
        print(f"DEBUG index_document: Created {len(splits)} chunks from {len(documents)} pages", file=sys.stderr)
        
        # Get or create vector store for this thread
        vector_store_manager = get_vector_store_manager()
        vector_store = vector_store_manager.get_or_create_store(thread_id)
        
        # Add documents to vector store
        vector_store.add_documents(documents=splits)
        
        print(f"DEBUG index_document: Successfully indexed {len(splits)} chunks", file=sys.stderr)
        
        # Also save to VFS for full text access
        full_text = "\n\n".join([doc.page_content for doc in documents])
        file_name = Path(file_path).stem + ".md"
        
        result_message = (
            f"Successfully indexed document: {file_name}\n"
            f"- {len(documents)} pages\n"
            f"- {len(splits)} chunks\n"
            f"- Ready for retrieval with retrieve_context tool\n"
            f"- Full text saved to VFS as {file_name}"
        )
        
        return Command(
            update={
                "files": {file_name: full_text},
                "messages": [
                    ToolMessage(result_message, tool_call_id=tool_call_id)
                ]
            }
        )
        
    except Exception as e:
        print(f"DEBUG index_document: Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return Command(
            update={
                "messages": [
                    ToolMessage(f"Error indexing document: {str(e)}", tool_call_id=tool_call_id)
                ]
            }
        )


@tool(response_format="content_and_artifact", description=RETRIEVE_CONTEXT_TOOL_DESCRIPTION)
def retrieve_context(
    query: str,
    config: RunnableConfig,
    k: int = 2
) -> tuple[str, list]:
    """Retrieve information from uploaded documents to help answer a query.
    
    This tool performs semantic search over documents that have been uploaded
    in the current conversation thread. Use this when you need to find specific
    information from user-provided documents.
    
    Args:
        query: The search query to find relevant document chunks
        config: LangGraph config containing thread_id
        k: Number of relevant document chunks to retrieve (default: 2)
    
    Returns:
        Tuple of (serialized context string, list of retrieved documents)
    """
    import sys
    
    # Get thread_id from RunnableConfig (LangGraph v1 way)
    thread_id = config.get("configurable", {}).get("thread_id")
    
    print(f"DEBUG retrieve_context: thread_id from RunnableConfig = {thread_id}", file=sys.stderr)
    
    if not thread_id:
        return "Warning: No thread_id found in config. Documents are isolated per thread. Ensure you're running the agent with a thread_id.", []
    
    vector_store_manager = get_vector_store_manager()
    
    # Debug: List all available threads
    all_threads = list(vector_store_manager._stores.keys())
    print(f"DEBUG retrieve_context: Available threads in vector store: {all_threads}", file=sys.stderr)
    print(f"DEBUG retrieve_context: Looking for documents in thread: {thread_id}", file=sys.stderr)
    
    vector_store = vector_store_manager.get_store(thread_id)
    
    if vector_store is None:
        return f"No documents have been uploaded in thread {thread_id}. Available threads: {all_threads}. Please ensure you upload documents in the same thread where you're asking questions.", []
    
    try:
        # Perform similarity search
        retrieved_docs = vector_store.similarity_search(query, k=k)
        
        if not retrieved_docs:
            return f"No relevant information found in the uploaded documents for this query. The vector store exists for thread {thread_id} but the search returned no results. Try a different query or upload relevant documents.", []
        
        print(f"DEBUG retrieve_context: Successfully retrieved {len(retrieved_docs)} documents", file=sys.stderr)
        
        # Serialize documents as per LangChain docs pattern
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\nContent: {doc.page_content}")
            for doc in retrieved_docs
        )
        
        return serialized, retrieved_docs
    except Exception as e:
        return f"Error retrieving context from thread {thread_id}: {str(e)}", []
