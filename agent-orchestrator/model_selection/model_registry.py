"""Model Registry - Loads and manages model definitions from YAML configuration."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from .types import (
    ModelDefinition,
    ModelCapabilities,
    Provider,
    CostLevel,
    LatencyLevel,
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Central registry for all available models and their capabilities."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self._models: Dict[str, ModelDefinition] = {}
        self._defaults: Dict[str, str] = {}
        self._loaded = False

    def _default_config_path(self) -> str:
        """Get default config path relative to this file."""
        return str(Path(__file__).parent.parent / "config" / "models.yaml")

    async def load(self) -> None:
        """Load model definitions from YAML config."""
        if self._loaded:
            return

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            for model_data in config.get("models", []):
                model = self._parse_model(model_data)
                self._models[model.name] = model
                logger.debug(f"Loaded model: {model.name} ({model.provider})")

            self._defaults = config.get("defaults", {})
            self._loaded = True
            logger.info(f"Model registry loaded: {len(self._models)} models")

        except FileNotFoundError:
            logger.warning(f"Model config not found at {self.config_path}, using defaults")
            self._load_defaults()
        except Exception as e:
            logger.error(f"Failed to load model config: {e}")
            self._load_defaults()

    def _parse_model(self, data: dict) -> ModelDefinition:
        """Parse a model definition from config data."""
        capabilities = ModelCapabilities(**data.get("capabilities", {}))
        return ModelDefinition(
            name=data["name"],
            provider=Provider(data["provider"]),
            cost_level=CostLevel(data["cost_level"]),
            latency=LatencyLevel(data["latency"]),
            max_tokens=data.get("max_tokens", 4000),
            available=data.get("available", True),
            capabilities=capabilities,
        )

    def _load_defaults(self) -> None:
        """Load minimal default models when config is unavailable."""
        self._models = {
            "gpt-4-turbo": ModelDefinition(
                name="gpt-4-turbo",
                provider=Provider.OPENAI,
                cost_level=CostLevel.HIGH,
                latency=LatencyLevel.MEDIUM,
                max_tokens=128000,
                capabilities=ModelCapabilities(reasoning=9, coding=9),
            ),
            "gpt-3.5-turbo": ModelDefinition(
                name="gpt-3.5-turbo",
                provider=Provider.OPENAI,
                cost_level=CostLevel.LOW,
                latency=LatencyLevel.FAST,
                max_tokens=16000,
                capabilities=ModelCapabilities(reasoning=6, coding=6, speed=9),
            ),
        }
        self._defaults = {"openai": "gpt-4-turbo"}
        self._loaded = True

    def get_model(self, name: str) -> Optional[ModelDefinition]:
        """Get a model by name."""
        return self._models.get(name)

    def get_all_models(self) -> List[ModelDefinition]:
        """Get all registered models."""
        return list(self._models.values())

    def get_available_models(self) -> List[ModelDefinition]:
        """Get all available (enabled) models."""
        return [m for m in self._models.values() if m.available]

    def get_models_by_provider(self, provider: Provider) -> List[ModelDefinition]:
        """Get all models for a specific provider."""
        return [m for m in self._models.values() if m.provider == provider]

    def get_default_model(self, provider: Optional[Provider] = None) -> Optional[ModelDefinition]:
        """Get the default model for a provider."""
        if provider:
            default_name = self._defaults.get(provider.value)
            if default_name:
                return self._models.get(default_name)
        # Fallback to first available OpenAI model
        openai_models = self.get_models_by_provider(Provider.OPENAI)
        return openai_models[0] if openai_models else None

    def get_models_with_capability(
        self, capability: str, min_score: int = 5
    ) -> List[ModelDefinition]:
        """Get models that meet a minimum capability score."""
        result = []
        for model in self.get_available_models():
            score = getattr(model.capabilities, capability, 0)
            if score >= min_score:
                result.append(model)
        return result


# Singleton instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get the model registry singleton."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
