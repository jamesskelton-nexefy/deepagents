"""Thread-aware vector store manager for RAG functionality."""
import os
from typing import Optional
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings


class VectorStoreManager:
    """Manages per-thread vector stores for document retrieval."""
    
    def __init__(self):
        """Initialize the vector store manager with OpenAI embeddings."""
        self._stores: dict[str, InMemoryVectorStore] = {}
        self._embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=os.environ.get("OPENAI_API_KEY")
        )
    
    def get_or_create_store(self, thread_id: str) -> InMemoryVectorStore:
        """Get or create a vector store for a specific thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            InMemoryVectorStore instance for the thread
        """
        if thread_id not in self._stores:
            self._stores[thread_id] = InMemoryVectorStore(self._embeddings)
        return self._stores[thread_id]
    
    def get_store(self, thread_id: str) -> Optional[InMemoryVectorStore]:
        """Get an existing vector store for a thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            InMemoryVectorStore if exists, None otherwise
        """
        return self._stores.get(thread_id)
    
    def clear_store(self, thread_id: str) -> None:
        """Clear the vector store for a specific thread.
        
        Args:
            thread_id: The thread identifier
        """
        if thread_id in self._stores:
            del self._stores[thread_id]
    
    def has_documents(self, thread_id: str) -> bool:
        """Check if a thread has any documents indexed.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            True if documents exist for this thread, False otherwise
        """
        store = self.get_store(thread_id)
        if store is None:
            return False
        # InMemoryVectorStore doesn't have a direct count method,
        # so we'll try a search and see if we get results
        try:
            results = store.similarity_search("", k=1)
            return len(results) > 0
        except:
            return False


# Global singleton instance
_vector_store_manager: Optional[VectorStoreManager] = None


def get_vector_store_manager() -> VectorStoreManager:
    """Get the global vector store manager instance.
    
    Returns:
        VectorStoreManager singleton instance
    """
    global _vector_store_manager
    if _vector_store_manager is None:
        _vector_store_manager = VectorStoreManager()
    return _vector_store_manager




