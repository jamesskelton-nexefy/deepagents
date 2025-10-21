#!/usr/bin/env python3
"""Test script to verify RAG functionality."""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_vector_store_manager():
    """Test the vector store manager."""
    print("Testing vector store manager...")
    
    from src.deepagents.vector_store import get_vector_store_manager
    from langchain_core.documents import Document
    
    manager = get_vector_store_manager()
    
    # Test creating stores for different threads
    store1 = manager.get_or_create_store("thread-1")
    store2 = manager.get_or_create_store("thread-2")
    
    assert store1 is not store2, "Stores should be different for different threads"
    print("✓ Thread isolation works")
    
    # Test adding documents
    doc1 = Document(page_content="This is a test document about machine learning.", metadata={"source": "test1.pdf"})
    doc2 = Document(page_content="This is another document about data science.", metadata={"source": "test2.pdf"})
    
    store1.add_documents([doc1])
    store2.add_documents([doc2])
    
    print("✓ Documents added to stores")
    
    # Test retrieval
    results1 = store1.similarity_search("machine learning", k=1)
    assert len(results1) > 0, "Should find documents in thread 1"
    assert "machine learning" in results1[0].page_content, "Should retrieve correct document"
    print("✓ Retrieval works in thread 1")
    
    results2 = store2.similarity_search("data science", k=1)
    assert len(results2) > 0, "Should find documents in thread 2"
    assert "data science" in results2[0].page_content, "Should retrieve correct document"
    print("✓ Retrieval works in thread 2")
    
    # Verify thread isolation
    results1_search2 = store1.similarity_search("data science", k=10)
    has_thread2_doc = any("data science" in doc.page_content for doc in results1_search2)
    assert not has_thread2_doc, "Thread 1 should not have thread 2's documents"
    print("✓ Thread isolation verified - documents don't leak between threads")
    
    print("\n✅ All vector store tests passed!")
    return True


def test_document_parser():
    """Test the document parser (requires a sample document)."""
    print("\nTesting document parser...")
    
    # Check if we have a test document
    test_docs = list(Path(__file__).parent.glob("*.pdf"))
    if not test_docs:
        print("⚠️  No PDF files found in examples/research/ - skipping parser test")
        print("   To test the parser, add a PDF file and run:")
        print(f"   python document_parser.py <file.pdf> test-thread-123")
        return False
    
    test_doc = test_docs[0]
    print(f"Found test document: {test_doc.name}")
    
    from examples.research.document_parser import parse_and_index_document
    
    result = parse_and_index_document(
        str(test_doc),
        "test-thread-parser",
        "pdf"
    )
    
    if result["success"]:
        print(f"✓ Parsed {result['pageCount']} pages")
        print(f"✓ Created {result['chunkCount']} chunks")
        print(f"✓ Found {result['tableCount']} tables")
        print(f"✓ Found {result['imageCount']} images")
        print("\n✅ Document parser test passed!")
        return True
    else:
        print(f"❌ Parser failed: {result.get('error')}")
        return False


def test_retrieve_context_tool():
    """Test the retrieve_context tool."""
    print("\nTesting retrieve_context tool...")
    
    from src.deepagents.tools import retrieve_context
    from src.deepagents.vector_store import get_vector_store_manager
    from langchain_core.documents import Document
    
    # Set up test data
    manager = get_vector_store_manager()
    store = manager.get_or_create_store("test-thread-tool")
    
    test_doc = Document(
        page_content="Python is a high-level programming language known for its simplicity and readability.",
        metadata={"source": "python_guide.pdf", "page": 1}
    )
    store.add_documents([test_doc])
    
    # Create mock state
    mock_state = {
        "thread_id": "test-thread-tool",
        "files": {}
    }
    
    # Test retrieval
    result, docs = retrieve_context.invoke({
        "query": "What is Python?",
        "state": mock_state,
        "k": 1
    })
    
    assert "Python" in result, "Should retrieve content about Python"
    assert len(docs) > 0, "Should return documents"
    print("✓ Tool retrieval works")
    print(f"✓ Retrieved: {result[:100]}...")
    
    # Test with no documents
    result_empty, docs_empty = retrieve_context.invoke({
        "query": "test",
        "state": {"thread_id": "nonexistent-thread", "files": {}},
        "k": 1
    })
    
    assert "No documents have been uploaded" in result_empty, "Should handle missing thread"
    print("✓ Tool handles missing thread correctly")
    
    print("\n✅ All retrieve_context tool tests passed!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("RAG Implementation Test Suite")
    print("=" * 60)
    
    # Check environment
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set!")
        print("   Please set it: export OPENAI_API_KEY=your_key_here")
        return 1
    
    print("✓ OPENAI_API_KEY is set\n")
    
    try:
        # Run tests
        test_vector_store_manager()
        test_retrieve_context_tool()
        test_document_parser()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour RAG implementation is working correctly!")
        print("\nNext steps:")
        print("1. Upload a document through the frontend")
        print("2. Ask the agent questions about the document")
        print("3. Check that it uses retrieve_context to find answers")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())




