"""Document parsing and indexing for RAG functionality."""
import os
from pathlib import Path
from typing import Dict, Any
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredPowerPointLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sys

# Add parent directory to path to import deepagents
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.deepagents.vector_store import get_vector_store_manager


def parse_and_index_document(
    file_path: str,
    thread_id: str,
    file_extension: str
) -> Dict[str, Any]:
    """Parse a document and index it in the thread's vector store.
    
    Args:
        file_path: Path to the uploaded document
        thread_id: Thread identifier for vector store isolation
        file_extension: File extension (pdf, docx, pptx)
    
    Returns:
        Dict containing parse results with success status, metadata, and content
    """
    try:
        # Load document based on file type
        if file_extension == "pdf":
            loader = PyPDFLoader(file_path)
        elif file_extension == "docx":
            loader = Docx2txtLoader(file_path)
        elif file_extension == "pptx":
            loader = UnstructuredPowerPointLoader(file_path)
        else:
            return {
                "success": False,
                "error": f"Unsupported file format: {file_extension}"
            }
        
        # Load the document
        documents = loader.load()
        
        if not documents:
            return {
                "success": False,
                "error": "Failed to extract content from document"
            }
        
        # Split documents into chunks for RAG
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)
        
        # Get or create vector store for this thread
        vector_store_manager = get_vector_store_manager()
        vector_store = vector_store_manager.get_or_create_store(thread_id)
        
        # Debug output
        print(f"DEBUG: Indexing {len(splits)} chunks for thread_id: {thread_id}", file=sys.stderr)
        
        # Add documents to vector store
        vector_store.add_documents(documents=splits)
        
        # Verify indexing worked
        test_results = vector_store.similarity_search("", k=1)
        print(f"DEBUG: After indexing, vector store has {len(test_results)} documents", file=sys.stderr)
        
        # Extract full text for markdown file
        full_text = "\n\n".join([doc.page_content for doc in documents])
        
        # Get document metadata
        page_count = len(documents)
        chunk_count = len(splits)
        
        # Calculate approximate table and image counts (basic heuristic)
        # This is a simple approach - more sophisticated parsing could be added
        table_count = sum(1 for doc in documents if "table" in doc.page_content.lower())
        image_count = sum(1 for doc in documents if "image" in doc.page_content.lower() or "figure" in doc.page_content.lower())
        
        return {
            "success": True,
            "fileName": Path(file_path).stem + ".md",
            "markdown": full_text,
            "pageCount": page_count,
            "chunkCount": chunk_count,
            "tableCount": table_count,
            "imageCount": image_count,
            "message": f"Successfully indexed {chunk_count} chunks from {page_count} pages"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error parsing document: {str(e)}"
        }


def main():
    """Command-line interface for document parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse and index a document for RAG")
    parser.add_argument("file_path", help="Path to the document file")
    parser.add_argument("thread_id", help="Thread ID for vector store isolation")
    parser.add_argument("--extension", "-e", help="File extension (pdf, docx, pptx)")
    
    args = parser.parse_args()
    
    # Determine extension if not provided
    extension = args.extension
    if not extension:
        extension = Path(args.file_path).suffix.lstrip(".")
    
    # Parse and index the document
    result = parse_and_index_document(args.file_path, args.thread_id, extension)
    
    # Print result as JSON
    import json
    print(json.dumps(result, indent=2))
    
    # Return appropriate exit code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

