"""
OpenRouter API support module
"""

from langchain_openai import ChatOpenAI
import os


def create_openrouter_model(model_name: str, temperature: float = 0.0):
    """
    Create OpenRouter model (temperature=0 fixed)
    
    Args:
        model_name: OpenRouter model name (e.g., "deepseek/deepseek-chat-v3-0324:free")
        temperature: Temperature setting (fixed value 0.0)
    
    Returns:
        ChatOpenAI: LangChain model using OpenRouter API
    
    Raises:
        ValueError: If OPENROUTER_API_KEY is not set
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable not set. "
            "Add OPENROUTER_API_KEY=your-key to .env file."
        )
    
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,  # Fixed value
        model_kwargs={
            "extra_headers": {
                "HTTP-Referer": "https://cyber-ai-fusion.lovable.app/",
                "X-Title": "AI Red Teaming Multi-Agent",
            }
        }
    )


def get_openrouter_api_key() -> str:
    """Query OpenRouter API key"""
    return os.getenv("OPENROUTER_API_KEY", "")


def is_openrouter_available() -> bool:
    """Check OpenRouter availability"""
    return bool(get_openrouter_api_key())
