"""
Embeddings client for generating vector embeddings using OpenAI.
"""
import logging
from typing import Optional
from openai import AsyncOpenAI

from config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingsClient:
    """Client for generating text embeddings using OpenAI API."""
    
    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
    
    async def generate(self, text: str) -> list[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise
    
    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single API call.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            logger.error(f"Batch embedding generation error: {e}")
            raise


# Singleton instance
_embeddings_client: Optional[EmbeddingsClient] = None


def get_embeddings_client() -> EmbeddingsClient:
    """Get the embeddings client singleton."""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = EmbeddingsClient()
    return _embeddings_client
