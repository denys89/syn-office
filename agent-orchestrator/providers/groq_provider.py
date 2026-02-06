"""Groq Provider - Implementation for Groq fast inference models."""

import logging
import os
from typing import Dict, List, Tuple, Optional

from .base import BaseModelProvider

logger = logging.getLogger(__name__)


class GroqProvider(BaseModelProvider):
    """Provider for Groq fast inference (Llama, Mixtral, etc)."""

    def __init__(self):
        super().__init__()
        self.name = "groq"
        self.client = None
        self.api_key: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize Groq client."""
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set, Groq provider unavailable")
            self._available = False
            self._initialized = True
            return

        try:
            # Import groq only when needed
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=self.api_key)
            self._available = True
            self._initialized = True
            logger.info("Groq provider initialized")
        except ImportError:
            logger.warning("groq package not installed")
            self._available = False
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            self._available = False
            self._initialized = True

    async def generate(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Tuple[str, Dict[str, int]]:
        """Generate a response using Groq."""
        if not self.client:
            raise RuntimeError("Groq client not initialized")

        response = await self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content or ""
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return content, token_usage

    async def health_check(self) -> bool:
        """Check if Groq is accessible."""
        if not self.client or not self._available:
            return False

        try:
            # Quick check - list models
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Groq health check failed: {e}")
            return False
