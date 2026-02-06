from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo"
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    
    # Groq
    groq_api_key: Optional[str] = None
    
    # Ollama (Local)
    ollama_url: str = "http://localhost:11434"
    ollama_enabled: bool = True
    
    # Model Selection
    models_config_path: str = "config/models.yaml"
    policies_config_path: str = "config/policies.yaml"
    default_model: str = "gpt-4-turbo"
    prefer_local_models: bool = True
    
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
    logger.info(f"Model Selection - Default: {settings.default_model}, Prefer Local: {settings.prefer_local_models}")
    return settings
