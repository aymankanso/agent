
import json
import os
import requests
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


class ModelProvider(str, Enum):
    """Supported LLM Providers (3 + OpenRouter commented out)"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    # OPENROUTER = "openrouter"  # Implement later
    OLLAMA = "ollama"


@dataclass
class ModelInfo:
    """Model information (3 fields only)"""
    display_name: str
    model_name: str
    provider: ModelProvider
    api_key_available: bool = False


def load_cloud_models() -> List[ModelInfo]:
    """Load OpenAI/Anthropic models from cloud_config.json"""
    config_path = Path(__file__).parent / "cloud_config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            models_data = json.load(f)
        
        models = []
        for model_data in models_data:
            try:
                provider = ModelProvider(model_data["provider"])
                api_key_available = validate_api_key(provider)
                
                models.append(ModelInfo(
                    display_name=model_data["display_name"],
                    model_name=model_data["model_name"], 
                    provider=provider,
                    api_key_available=api_key_available
                ))
            except (ValueError, KeyError):
                # Skip unsupported providers or invalid formats
                continue
        
        return models
        
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_local_model_mappings() -> Dict[str, str]:
    """Load model_name -> display_name mapping from local_config.json"""
    config_path = Path(__file__).parent / "local_config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            models_data = json.load(f)
        
        # Create model_name -> display_name mapping dictionary
        mappings = {}
        for model_data in models_data:
            try:
                if model_data.get("provider") == "ollama":
                    mappings[model_data["model_name"]] = model_data["display_name"]
            except KeyError:
                continue
        
        return mappings
        
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_ollama_models_with_mappings() -> List[ModelInfo]:
    """Get actually installed Ollama models and apply display name mapping from config file"""
    # Load mappings from config file
    display_name_mappings = load_local_model_mappings()
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            models = []
            
            for model in models_data:
                model_name = model["name"]
                
                # Use mapping if in config file, otherwise use default format
                if model_name in display_name_mappings:
                    display_name = display_name_mappings[model_name]
                else:
                    display_name = f"{model_name} (Installed)"
                
                models.append(ModelInfo(
                    display_name=display_name,
                    model_name=model_name,
                    provider=ModelProvider.OLLAMA,
                    api_key_available=True
                ))
            
            return models
    except requests.RequestException:
        pass
    
    return []


# OpenRouter related code commented out (implement later)
# def get_openrouter_models() -> List[ModelInfo]:
#     """OpenRouter models (configured default models)"""
#     if not os.getenv("OPENROUTER_API_KEY"):
#         return []
#     
#     # Provide only popular OpenRouter models
#     openrouter_models = [
#         {
#             "display_name": "DeepSeek Chat (Free)",
#             "model_name": "deepseek/deepseek-chat-v3-0324:free",
#             "provider": "openrouter"
#         },
#         # ... Other models
#     ]
#     
#     return [ModelInfo(...) for model in openrouter_models]


def validate_api_key(provider: ModelProvider) -> bool:
    """Validate API key"""
    key_map = {
        ModelProvider.OPENAI: "OPENAI_API_KEY",
        ModelProvider.ANTHROPIC: "ANTHROPIC_API_KEY", 
        # ModelProvider.OPENROUTER: "OPENROUTER_API_KEY"  # Commented out
    }
    
    if provider == ModelProvider.OLLAMA:
        # Check Ollama connection
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    required_key = key_map.get(provider)
    return bool(os.getenv(required_key)) if required_key else False


def check_ollama_connection() -> Dict[str, Any]:
    """Check Ollama connection status (maintain compatibility with existing code)"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {
                "connected": True,
                "url": "http://localhost:11434",
                "models": [model.get("name", "") for model in models],
                "count": len(models)
            }
        else:
            return {
                "connected": False,
                "url": "http://localhost:11434",
                "error": f"HTTP {response.status_code}",
                "models": [],
                "count": 0
            }
    except requests.RequestException as e:
        return {
            "connected": False,
            "url": "http://localhost:11434",
            "error": str(e),
            "models": [],
            "count": 0
        }


def list_available_models() -> List[Dict[str, Any]]:
    """List of all available models (used in CLI) - Simplified duplicate removal"""
    all_models = []
    
    # Cloud models (OpenAI/Anthropic)
    all_models.extend(load_cloud_models())
    
    # Ollama models (actually installed + config file mapping)
    all_models.extend(get_ollama_models_with_mappings())
    
    # OpenRouter models (commented out)  
    # all_models.extend(get_openrouter_models())
    
    return [
        {
            "display_name": model.display_name,
            "model_name": model.model_name,
            "provider": model.provider.value,
            "api_key_available": model.api_key_available
        }
        for model in all_models
    ]


def load_llm_model(model_name: str, provider: str, temperature: float = 0.0):
    """Load actual LLM model - Use Chat class directly for each provider"""
    try:
        provider_enum = ModelProvider(provider)
    except ValueError:
        raise ValueError(f"Unsupported provider: {provider}")
    
    # Use Chat class directly for each provider (temperature=0 fixed)
    if provider_enum == ModelProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            temperature=0
        )
    
    elif provider_enum == ModelProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            temperature=0
        )
    
    elif provider_enum == ModelProvider.OLLAMA:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model_name,
            temperature=0
        )
    
    # OpenRouter commented out
    # elif provider_enum == ModelProvider.OPENROUTER:
    #     from .openrouter import create_openrouter_model
    #     return create_openrouter_model(model_name, 0)
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# Export main functions
__all__ = [
    "load_llm_model", 
    "list_available_models",
    "validate_api_key",
    "check_ollama_connection",
    "ModelProvider",
    "ModelInfo",
    # Core functions
    "load_cloud_models",
    "load_local_model_mappings",
    "get_ollama_models_with_mappings"
]
