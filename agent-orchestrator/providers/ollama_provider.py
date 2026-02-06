"""Ollama Provider - Implementation for local Ollama models."""

import logging
import os
from typing import Dict, List, Tuple, Optional
import httpx

from .base import BaseModelProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseModelProvider):
    """Provider for local Ollama models."""

    def __init__(self, base_url: Optional[str] = None):
        super().__init__()
        self.name = "ollama"
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize Ollama client."""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,  # Longer timeout for local inference
            )
            
            # Check if Ollama is running
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                self._available = True
                models = response.json().get("models", [])
                logger.info(f"Ollama provider initialized with {len(models)} models")
            else:
                self._available = False
                logger.warning(f"Ollama not available: {response.status_code}")
            
            self._initialized = True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._available = False
            self._initialized = True

    async def generate(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Tuple[str, Dict[str, int]]:
        """Generate a response using Ollama."""
        if not self.client:
            raise RuntimeError("Ollama client not initialized")

        # Ollama uses the /api/chat endpoint
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data.get("message", {}).get("content", "")
        
        # Ollama provides eval_count and prompt_eval_count
        token_usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }

        return content, token_usage

    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        if not self.client or not self._available:
            return False

        try:
            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available models in Ollama."""
        if not self.client or not self._available:
            return []

        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get("name", "") for m in models]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
        
        return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        if not self.client:
            return False

        try:
            response = await self.client.post(
                "/api/pull",
                json={"name": model_name},
                timeout=600.0,  # Long timeout for model download
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
