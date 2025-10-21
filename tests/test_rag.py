"""Unit tests for RAG (Retrieval Augmented Generation) functionality."""
import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document

from src.deepagents.vector_store import VectorStoreManager, get_vector_store_manager
from src.deepagents.tools import retrieve_context


class TestVectorStoreManager:
    """Tests for VectorStoreManager class."""
    
    def test_get_or_create_store_creates_new_store(self):
        """Test that get_or_create_store creates a new store for a new thread."""
        manager = VectorStoreManager()
        thread_id = "test-thread-1"
        
        store = manager.get_or_create_store(thread_id)
        
        assert store is not None
        assert thread_id in manager._stores
    
    def test_get_or_create_store_returns_existing_store(self):
        """Test that get_or_create_store returns existing store for same thread."""
        manager = VectorStoreManager()
        thread_id = "test-thread-2"
        
        store1 = manager.get_or_create_store(thread_id)
        store2 = manager.get_or_create_store(thread_id)
        
        assert store1 is store2
    
    def test_get_store_returns_none_for_nonexistent_thread(self):
        """Test that get_store returns None for non-existent thread."""
        manager = VectorStoreManager()
        
        store = manager.get_store("nonexistent-thread")
        
        assert store is None
    
    def test_get_store_returns_existing_store(self):
        """Test that get_store returns existing store."""
        manager = VectorStoreManager()
        thread_id = "test-thread-3"
        
        created_store = manager.get_or_create_store(thread_id)
        retrieved_store = manager.get_store(thread_id)
        
        assert retrieved_store is created_store
    
    def test_clear_store_removes_store(self):
        """Test that clear_store removes store for thread."""
        manager = VectorStoreManager()
        thread_id = "test-thread-4"
        
        manager.get_or_create_store(thread_id)
        manager.clear_store(thread_id)
        
        assert manager.get_store(thread_id) is None
    
    def test_clear_store_handles_nonexistent_thread(self):
        """Test that clear_store handles non-existent thread gracefully."""
        manager = VectorStoreManager()
        
        # Should not raise an error
        manager.clear_store("nonexistent-thread")
    
    def test_thread_isolation(self):
        """Test that different threads have separate vector stores."""
        manager = VectorStoreManager()
        thread1 = "thread-1"
        thread2 = "thread-2"
        
        store1 = manager.get_or_create_store(thread1)
        store2 = manager.get_or_create_store(thread2)
        
        assert store1 is not store2


class TestRetrieveContext:
    """Tests for retrieve_context tool."""
    
    @patch('src.deepagents.tools.get_vector_store_manager')
    def test_retrieve_context_no_documents(self, mock_get_manager):
        """Test retrieve_context when no documents have been uploaded."""
        # Mock the vector store manager to return None
        mock_manager = Mock()
        mock_manager.get_store.return_value = None
        mock_get_manager.return_value = mock_manager
        
        # Create a mock state
        mock_state = Mock()
        mock_state.thread_id = "test-thread"
        
        # Call retrieve_context
        result, docs = retrieve_context.invoke({
            "query": "test query",
            "state": mock_state
        })
        
        assert "No documents have been uploaded" in result
        assert docs == []
    
    @patch('src.deepagents.tools.get_vector_store_manager')
    def test_retrieve_context_with_documents(self, mock_get_manager):
        """Test retrieve_context successfully retrieves documents."""
        # Create mock documents
        mock_docs = [
            Document(
                page_content="This is the first document chunk.",
                metadata={"source": "test.pdf", "page": 1}
            ),
            Document(
                page_content="This is the second document chunk.",
                metadata={"source": "test.pdf", "page": 2}
            )
        ]
        
        # Mock the vector store
        mock_store = Mock()
        mock_store.similarity_search.return_value = mock_docs
        
        # Mock the manager
        mock_manager = Mock()
        mock_manager.get_store.return_value = mock_store
        mock_get_manager.return_value = mock_manager
        
        # Create a mock state
        mock_state = Mock()
        mock_state.thread_id = "test-thread"
        
        # Call retrieve_context
        result, docs = retrieve_context.invoke({
            "query": "test query",
            "state": mock_state,
            "k": 2
        })
        
        # Verify the result
        assert "Source:" in result
        assert "This is the first document chunk" in result
        assert "This is the second document chunk" in result
        assert docs == mock_docs
        
        # Verify similarity_search was called correctly
        mock_store.similarity_search.assert_called_once_with("test query", k=2)
    
    @patch('src.deepagents.tools.get_vector_store_manager')
    def test_retrieve_context_no_relevant_documents(self, mock_get_manager):
        """Test retrieve_context when no relevant documents are found."""
        # Mock the vector store to return empty list
        mock_store = Mock()
        mock_store.similarity_search.return_value = []
        
        # Mock the manager
        mock_manager = Mock()
        mock_manager.get_store.return_value = mock_store
        mock_get_manager.return_value = mock_manager
        
        # Create a mock state
        mock_state = Mock()
        mock_state.thread_id = "test-thread"
        
        # Call retrieve_context
        result, docs = retrieve_context.invoke({
            "query": "test query",
            "state": mock_state
        })
        
        assert "No relevant information found" in result
        assert docs == []
    
    @patch('src.deepagents.tools.get_vector_store_manager')
    def test_retrieve_context_error_handling(self, mock_get_manager):
        """Test retrieve_context handles errors gracefully."""
        # Mock the vector store to raise an exception
        mock_store = Mock()
        mock_store.similarity_search.side_effect = Exception("Test error")
        
        # Mock the manager
        mock_manager = Mock()
        mock_manager.get_store.return_value = mock_store
        mock_get_manager.return_value = mock_manager
        
        # Create a mock state
        mock_state = Mock()
        mock_state.thread_id = "test-thread"
        
        # Call retrieve_context
        result, docs = retrieve_context.invoke({
            "query": "test query",
            "state": mock_state
        })
        
        assert "Error retrieving context" in result
        assert docs == []


class TestDocumentIndexing:
    """Tests for document indexing functionality."""
    
    @patch('src.deepagents.vector_store.get_vector_store_manager')
    def test_document_chunks_added_to_store(self, mock_get_manager):
        """Test that document chunks are properly added to vector store."""
        # This is an integration-style test that would require
        # the actual document_parser module
        # For now, we'll keep it as a placeholder
        pass
    
    def test_thread_isolation_for_documents(self):
        """Test that documents are isolated between threads."""
        manager = VectorStoreManager()
        
        # Create mock documents
        doc1 = Document(page_content="Thread 1 content", metadata={"source": "doc1.pdf"})
        doc2 = Document(page_content="Thread 2 content", metadata={"source": "doc2.pdf"})
        
        # Add to different threads
        store1 = manager.get_or_create_store("thread-1")
        store2 = manager.get_or_create_store("thread-2")
        
        store1.add_documents([doc1])
        store2.add_documents([doc2])
        
        # Search in thread 1 should only return thread 1 docs
        results1 = store1.similarity_search("content", k=10)
        assert len(results1) >= 1
        assert all("Thread 1" in doc.page_content for doc in results1)
        
        # Search in thread 2 should only return thread 2 docs
        results2 = store2.similarity_search("content", k=10)
        assert len(results2) >= 1
        assert all("Thread 2" in doc.page_content for doc in results2)


def test_get_vector_store_manager_singleton():
    """Test that get_vector_store_manager returns singleton instance."""
    manager1 = get_vector_store_manager()
    manager2 = get_vector_store_manager()
    
    assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




