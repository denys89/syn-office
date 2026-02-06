"""Model Providers package - Abstract interface for multiple LLM providers."""

from .base import BaseModelProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider

from typing import Optional
from model_selection.types import Provider

# Provider instances (lazy initialized)
_providers: dict = {}


async def get_provider_for(provider: Provider) -> Optional[BaseModelProvider]:
    """
    Get a provider instance for the specified provider type.
    
    Providers are lazily initialized on first access.
    """
    global _providers

    if provider.value in _providers:
        return _providers[provider.value]

    try:
        if provider == Provider.OPENAI:
            instance = OpenAIProvider()
        elif provider == Provider.ANTHROPIC:
            instance = AnthropicProvider()
        elif provider == Provider.GROQ:
            instance = GroqProvider()
        elif provider == Provider.OLLAMA:
            instance = OllamaProvider()
        else:
            return None

        await instance.initialize()
        _providers[provider.value] = instance
        return instance

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to initialize {provider.value}: {e}")
        return None


__all__ = [
    "BaseModelProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GroqProvider",
    "OllamaProvider",
    "get_provider_for",
]
