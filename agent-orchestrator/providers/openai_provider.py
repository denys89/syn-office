"""OpenAI Provider - Implementation for OpenAI models."""

import logging
import os
from typing import Dict, List, Tuple, Optional

from openai import AsyncOpenAI

from .base import BaseModelProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseModelProvider):
    """Provider for OpenAI models (GPT-4, GPT-3.5, etc)."""

    def __init__(self):
        super().__init__()
        self.name = "openai"
        self.client: Optional[AsyncOpenAI] = None

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, OpenAI provider unavailable")
            self._available = False
            self._initialized = True
            return

        try:
            self.client = AsyncOpenAI(api_key=api_key)
            self._available = True
            self._initialized = True
            logger.info("OpenAI provider initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self._available = False
            self._initialized = True

    async def generate(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Tuple[str, Dict[str, int]]:
        """Generate a response using OpenAI."""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

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
        """Check if OpenAI is accessible."""
        if not self.client or not self._available:
            return False

        try:
            # Quick validation - list models
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
