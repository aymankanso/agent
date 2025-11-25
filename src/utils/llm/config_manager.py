"""
Memory-based configuration manager - Manages in memory only without file storage
"""

from dataclasses import dataclass
from typing import Optional, Any
from .models import load_llm_model, ModelProvider
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration"""
    model_name: str = "gpt-4o-mini"
    provider: str = "openai"
    display_name: str = "GPT-4o Mini"
    temperature: float = 0.0


class MemoryConfigManager:
    """Memory-based configuration manager - Does not save to file"""
    
    _instance: Optional['MemoryConfigManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self._config: Optional[LLMConfig] = None
            self._llm_instance: Optional[Any] = None
            self._initialized = True
    
    @property
    def config(self) -> LLMConfig:
        """Return current configuration (can use default values)"""
        if self._config is None:
            self._config = LLMConfig()  # Default values
        return self._config
    
    @property
    def llm_instance(self) -> Optional[Any]:
        """Return current LLM instance"""
        return self._llm_instance
    
    def update_config(self, model_name: str, provider: str, display_name: str) -> None:
        """Update LLM configuration (stored in memory only)"""
        self._config = LLMConfig(
            model_name=model_name,
            provider=provider,
            display_name=display_name,
            temperature=0.0  # Fixed value
        )
        
        # Create new LLM instance too
        try:
            self._llm_instance = load_llm_model(
                model_name=model_name,
                provider=provider,
                temperature=0.0
            )
        except Exception as e:
            logger.warning(f"Failed to load LLM model: {e}")
            self._llm_instance = None
    
    def get_current_llm(self) -> Optional[Any]:
        """Return current LLM instance (create with default if none)"""
        if self._llm_instance is None and self._config is not None:
            try:
                self._llm_instance = load_llm_model(
                    model_name=self._config.model_name,
                    provider=self._config.provider,
                    temperature=0.0
                )
            except Exception as e:
                logger.warning(f"Failed to load LLM model: {e}")
                return None
        
        return self._llm_instance
    
    def reset(self) -> None:
        """Reset configuration"""
        self._config = None
        self._llm_instance = None


# Global instance (singleton)
_memory_config_manager: Optional[MemoryConfigManager] = None


def get_memory_config_manager() -> MemoryConfigManager:
    """Return global memory configuration manager instance"""
    global _memory_config_manager
    if _memory_config_manager is None:
        _memory_config_manager = MemoryConfigManager()
    return _memory_config_manager


def get_current_llm_config() -> LLMConfig:
    """Query current LLM configuration (from memory)"""
    return get_memory_config_manager().config


def update_llm_config(model_name: str, provider: str, display_name: str, 
                     temperature: float = 0.0) -> None:
    """Update LLM configuration (stored in memory only)"""
    get_memory_config_manager().update_config(
        model_name=model_name,
        provider=provider,
        display_name=display_name
    )


def get_current_llm():
    """Return current LLM instance"""
    return get_memory_config_manager().get_current_llm()


def reset_config() -> None:
    """Reset configuration"""
    get_memory_config_manager().reset()


# Export main functions
__all__ = [
    "LLMConfig",
    "MemoryConfigManager",
    "get_current_llm_config", 
    "update_llm_config",
    "get_current_llm",
    "reset_config"
]
