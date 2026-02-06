"""Tests for Model Registry."""

import pytest
from pathlib import Path
import tempfile
import yaml

from model_selection.model_registry import ModelRegistry
from model_selection.types import Provider, CostLevel


class TestModelRegistry:
    """Test suite for ModelRegistry."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config file."""
        config = {
            "models": [
                {
                    "name": "test-model-1",
                    "provider": "openai",
                    "cost_level": "high",
                    "latency": "medium",
                    "max_tokens": 128000,
                    "available": True,
                    "capabilities": {
                        "reasoning": 9,
                        "coding": 8,
                    },
                },
                {
                    "name": "test-model-2",
                    "provider": "ollama",
                    "cost_level": "free",
                    "latency": "fast",
                    "max_tokens": 8000,
                    "available": True,
                    "capabilities": {
                        "reasoning": 6,
                        "coding": 6,
                    },
                },
                {
                    "name": "disabled-model",
                    "provider": "openai",
                    "cost_level": "low",
                    "latency": "fast",
                    "max_tokens": 16000,
                    "available": False,
                    "capabilities": {},
                },
            ],
            "defaults": {
                "openai": "test-model-1",
                "ollama": "test-model-2",
            },
        }
        
        config_path = tmp_path / "models.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        
        return str(config_path)

    @pytest.mark.asyncio
    async def test_load_models_from_config(self, temp_config):
        """Test loading models from YAML config."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        models = registry.get_all_models()
        assert len(models) == 3

    @pytest.mark.asyncio
    async def test_get_model_by_name(self, temp_config):
        """Test getting a specific model."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        model = registry.get_model("test-model-1")
        assert model is not None
        assert model.name == "test-model-1"
        assert model.provider == Provider.OPENAI

    @pytest.mark.asyncio
    async def test_get_nonexistent_model_returns_none(self, temp_config):
        """Test that getting a nonexistent model returns None."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        model = registry.get_model("nonexistent-model")
        assert model is None

    @pytest.mark.asyncio
    async def test_get_available_models_excludes_disabled(self, temp_config):
        """Test that disabled models are excluded from available list."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        available = registry.get_available_models()
        assert len(available) == 2
        assert all(m.available for m in available)

    @pytest.mark.asyncio
    async def test_get_models_by_provider(self, temp_config):
        """Test filtering models by provider."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        openai_models = registry.get_models_by_provider(Provider.OPENAI)
        assert len(openai_models) == 2  # Including disabled one
        
        ollama_models = registry.get_models_by_provider(Provider.OLLAMA)
        assert len(ollama_models) == 1

    @pytest.mark.asyncio
    async def test_get_default_model(self, temp_config):
        """Test getting default model for a provider."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        default = registry.get_default_model(Provider.OPENAI)
        assert default is not None
        assert default.name == "test-model-1"

    @pytest.mark.asyncio
    async def test_get_models_with_capability(self, temp_config):
        """Test filtering models by capability threshold."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        # Get models with coding >= 7
        capable = registry.get_models_with_capability("coding", min_score=7)
        assert len(capable) == 1
        assert capable[0].name == "test-model-1"

    @pytest.mark.asyncio
    async def test_load_defaults_when_config_missing(self):
        """Test that default models are loaded when config is missing."""
        registry = ModelRegistry(config_path="/nonexistent/path.yaml")
        await registry.load()
        
        models = registry.get_all_models()
        assert len(models) > 0
        # Should have at least GPT-4 and GPT-3.5 as defaults
        assert registry.get_model("gpt-4-turbo") is not None

    @pytest.mark.asyncio
    async def test_model_capabilities_parsed(self, temp_config):
        """Test that model capabilities are properly parsed."""
        registry = ModelRegistry(config_path=temp_config)
        await registry.load()
        
        model = registry.get_model("test-model-1")
        assert model.capabilities.reasoning == 9
        assert model.capabilities.coding == 8
        # Defaults should be 5
        assert model.capabilities.summarization == 5
