"""Base Model Provider - Abstract interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BaseModelProvider(ABC):
    """
    Abstract base class for model providers.
    
    All providers must implement these methods to support
    the model selection engine's execution flow.
    """

    def __init__(self):
        self.name: str = "base"
        self._initialized: bool = False
        self._available: bool = False

    async def initialize(self) -> None:
        """
        Initialize the provider.
        
        Override this to perform async initialization (API key validation, etc).
        """
        self._initialized = True

    @abstractmethod
    async def generate(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Tuple[str, Dict[str, int]]:
        """
        Generate a response from the model.
        
        Args:
            model_name: The specific model to use
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Tuple of (response_content, token_usage_dict)
            token_usage_dict should have: prompt_tokens, completion_tokens, total_tokens
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available and working.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available

    def is_initialized(self) -> bool:
        """Check if provider is initialized."""
        return self._initialized
