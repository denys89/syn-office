"""Anthropic Provider - Implementation for Claude models."""

import logging
import os
from typing import Dict, List, Tuple, Optional

from .base import BaseModelProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseModelProvider):
    """Provider for Anthropic Claude models."""

    def __init__(self):
        super().__init__()
        self.name = "anthropic"
        self.client = None
        self.api_key: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize Anthropic client."""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set, Anthropic provider unavailable")
            self._available = False
            self._initialized = True
            return

        try:
            # Import anthropic only when needed
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            self._available = True
            self._initialized = True
            logger.info("Anthropic provider initialized")
        except ImportError:
            logger.warning("anthropic package not installed")
            self._available = False
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic: {e}")
            self._available = False
            self._initialized = True

    async def generate(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Tuple[str, Dict[str, int]]:
        """Generate a response using Anthropic Claude."""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        # Anthropic requires system message to be separate
        system_content = ""
        chat_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        response = await self.client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            system=system_content,
            messages=chat_messages,
            temperature=temperature,
        )

        content = response.content[0].text if response.content else ""
        token_usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        return content, token_usage

    async def health_check(self) -> bool:
        """Check if Anthropic is accessible."""
        if not self.client or not self._available:
            return False

        try:
            # Simple check - try to count tokens
            await self.client.messages.count_tokens(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            # Even if count_tokens fails, the client might still work
            return self._available
