from pydantic_settings import BaseSettings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    
    # Database
    database_url: str = "postgres://synoffice:synoffice_secret@localhost:5432/synoffice"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    
    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    
    # Backend API
    backend_url: str = "http://localhost:8080"
    internal_api_key: str = "dev-internal-key-change-in-production"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    logger.info(f"Settings loaded - Backend URL: {settings.backend_url}")
    logger.info(f"Settings loaded - Internal API Key: {settings.internal_api_key[:10]}... (length: {len(settings.internal_api_key)})")
    return settings
