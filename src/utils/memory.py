
import os
import logging
from typing import Optional
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

logger = logging.getLogger(__name__)

# Global instances
_checkpointer: Optional[InMemorySaver] = None
_store: Optional[InMemoryStore] = None

def get_checkpointer() -> InMemorySaver:
    """
    Return centralized Checkpointer instance
    
    Returns:
        InMemorySaver: Memory-based checkpointer
    """
    global _checkpointer
    
    if _checkpointer is None:
        _checkpointer = InMemorySaver()
        logger.info("InMemorySaver checkpointer initialized")
    
    return _checkpointer

def get_store() -> InMemoryStore:
    """
    Return centralized Store instance
    
    Returns:
        InMemoryStore: Memory-based store (includes vector index)
    """
    global _store
    
    if _store is None:
        # Check for OpenAI API key to enable semantic search
        if os.getenv("OPENAI_API_KEY"):
            index_config = {
                "dims": 1536,
                "embed": "openai:text-embedding-3-small",
            }
            logger.info("InMemoryStore initialized with OpenAI embeddings")
        else:
            # Fallback: No embeddings (semantic search disabled)
            index_config = None
            logger.warning("OPENAI_API_KEY not found. InMemoryStore initialized WITHOUT embeddings. Semantic search will be disabled.")

        _store = InMemoryStore(
            index=index_config
        )
    
    return _store

def reset_persistence():
    """
    For development: Reset all persistence instances
    """
    global _checkpointer, _store
    
    _checkpointer = None
    _store = None
    logger.info("Persistence instances reset")

def clear_thread_checkpoint(thread_id: str):
    """
    Clear checkpoint history for a specific thread
    
    This removes all stored conversation history for the given thread,
    forcing LangGraph to start fresh on the next invocation.
    
    Args:
        thread_id: The thread ID to clear
    """
    global _checkpointer
    
    if _checkpointer is not None:
        try:
            
            config = {"configurable": {"thread_id": thread_id}}
           
            if hasattr(_checkpointer, 'storage'):
                
                keys_to_remove = [k for k in _checkpointer.storage.keys() if thread_id in str(k)]
                for key in keys_to_remove:
                    del _checkpointer.storage[key]
                logger.info(f"Cleared {len(keys_to_remove)} checkpoint entries for thread {thread_id}")
        except Exception as e:
            logger.warning(f"Failed to clear checkpoint for thread {thread_id}: {e}")
           
            _checkpointer = InMemorySaver()
            logger.info("Resetted entire checkpointer as fallback")

def get_persistence_status() -> dict:
    """
    Return current persistence status (for debugging)
    
    Returns:
        dict: Current status information
    """
    return {
        "checkpointer_initialized": _checkpointer is not None,
        "store_initialized": _store is not None,
        "checkpointer_type": type(_checkpointer).__name__ if _checkpointer else None,
        "store_type": type(_store).__name__ if _store else None,
    }

def create_thread_config(user_id: str, conversation_id: Optional[str] = None) -> dict:
    """
    Create thread-specific configuration
    
    Args:
        user_id: User ID
        conversation_id: Conversation ID (optional)
    
    Returns:
        dict: LangGraph config dictionary
    """
    thread_id = f"user_{user_id}"
    if conversation_id:
        thread_id += f"_conv_{conversation_id}"
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "main",
            "recursion_limit": 30  
        }
    }
    
    logger.debug(f"Created thread config: {config}")
    return config

# Helper functions for development convenience
def create_memory_namespace(user_id: str, namespace_type: str = "memories") -> tuple:
    """
    Create memory namespace
    
    Args:
        user_id: User ID
        namespace_type: Namespace type (memories, preferences, etc.)
    
    Returns:
        tuple: LangMem namespace tuple
    """
    return (namespace_type, user_id)

def get_debug_info() -> dict:
    """
    Return debugging information
    
    Returns:
        dict: Current persistence status and statistics
    """
    status = get_persistence_status()
    
   
    debug_info = status.copy()
    
    if _checkpointer:
        
        debug_info["checkpointer_class"] = str(type(_checkpointer))
    
    if _store:
        debug_info["store_class"] = str(type(_store))
       
        try:
            debug_info["store_has_index"] = hasattr(_store, 'index')
        except:
            debug_info["store_has_index"] = False
    
    return debug_info
