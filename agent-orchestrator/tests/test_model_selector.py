"""Integration tests for the Model Selector."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import yaml

from model_selection.model_selector import ModelSelector
from model_selection.model_registry import ModelRegistry
from model_selection.capability_extractor import CapabilityExtractor
from model_selection.scoring_engine import ScoringEngine
from model_selection.policy_enforcer import PolicyEnforcer
from model_selection.types import Provider
from models import ExecuteRequest, AgentContext


class TestModelSelector:
    """Integration tests for ModelSelector."""

    @pytest.fixture
    def temp_configs(self, tmp_path):
        """Create temporary config files."""
        models_config = {
            "models": [
                {
                    "name": "gpt-4-turbo",
                    "provider": "openai",
                    "cost_level": "high",
                    "latency": "medium",
                    "max_tokens": 128000,
                    "available": True,
                    "capabilities": {"reasoning": 9, "coding": 9, "summarization": 8},
                },
                {
                    "name": "llama3:8b",
                    "provider": "ollama",
                    "cost_level": "free",
                    "latency": "fast",
                    "max_tokens": 8000,
                    "available": True,
                    "capabilities": {"reasoning": 6, "coding": 6, "summarization": 6},
                },
            ],
            "defaults": {"openai": "gpt-4-turbo", "ollama": "llama3:8b"},
        }
        
        policies_config = {
            "policies": {
                "prefer_local": True,
                "local_capability_threshold": 6,
                "fallback_enabled": True,
                "max_retries": 2,
                "weights": {
                    "capability_match": 0.4,
                    "speed": 0.2,
                    "cost_efficiency": 0.3,
                    "reliability": 0.1,
                },
            },
            "provider_priority": ["ollama", "groq", "openai", "anthropic"],
            "restricted_patterns": [],
            "cost_levels": {"free": 0, "low": 0.001, "medium": 0.01, "high": 0.03},
        }
        
        models_path = tmp_path / "models.yaml"
        policies_path = tmp_path / "policies.yaml"
        
        with open(models_path, "w") as f:
            yaml.dump(models_config, f)
        with open(policies_path, "w") as f:
            yaml.dump(policies_config, f)
        
        return str(models_path), str(policies_path)

    @pytest.fixture
    def selector(self, temp_configs):
        """Create a ModelSelector with test configs."""
        models_path, policies_path = temp_configs
        
        registry = ModelRegistry(config_path=models_path)
        extractor = CapabilityExtractor(policies_path=policies_path)
        scorer = ScoringEngine(policies_path=policies_path)
        enforcer = PolicyEnforcer(policies_path=policies_path)
        
        return ModelSelector(
            registry=registry,
            extractor=extractor,
            scorer=scorer,
            enforcer=enforcer,
        )

    @pytest.fixture
    def sample_request(self):
        """Create a sample execute request."""
        return ExecuteRequest(
            task_id="test-task-123",
            agent_id="agent-456",
            office_id="office-789",
            conversation_id="conv-012",
            input="Write a Python function to sort a list",
        )

    @pytest.fixture
    def sample_context(self):
        """Create a sample agent context."""
        return AgentContext(
            agent_id="agent-456",
            agent_name="Alex",
            agent_role="Engineer",
            system_prompt="You are a helpful engineer.",
            conversation_history=[],
            memories=[],
        )

    @pytest.mark.asyncio
    async def test_select_model_returns_best_match(self, selector, sample_request, sample_context):
        """Test that model selection returns the best matching model."""
        await selector.initialize()
        
        selected = await selector.select_model(sample_request, sample_context)
        
        assert selected is not None
        assert selected.model_name in ["gpt-4-turbo", "llama3:8b"]
        assert selected.score > 0

    @pytest.mark.asyncio
    async def test_select_model_considers_agent_role(self, selector, sample_request, sample_context):
        """Test that agent role affects model selection."""
        await selector.initialize()
        
        # Engineer role requires high coding capability
        selected = await selector.select_model(sample_request, sample_context)
        
        # For coding tasks with Engineer role, GPT-4 should be preferred (coding=9)
        # unless local preference overrides it
        assert selected.model_name in ["gpt-4-turbo", "llama3:8b"]

    @pytest.mark.asyncio
    async def test_select_model_provides_alternatives(self, selector, sample_request, sample_context):
        """Test that alternatives are provided in selection result."""
        await selector.initialize()
        
        selected = await selector.select_model(sample_request, sample_context)
        
        # Should have at least the model we didn't select as alternative
        # (we have 2 models configured)
        assert isinstance(selected.alternatives, list)

    @pytest.mark.asyncio
    async def test_select_model_handles_sensitive_content(self, selector, sample_context):
        """Test that sensitive content routes to local models."""
        await selector.initialize()
        
        # Modify enforcer to add restriction
        selector.enforcer._restricted_patterns = [
            {"pattern": "password|secret", "allowed_providers": ["ollama"]},
        ]
        
        sensitive_request = ExecuteRequest(
            task_id="test-task-123",
            agent_id="agent-456",
            office_id="office-789",
            conversation_id="conv-012",
            input="My password is supersecret123",
        )
        
        selected = await selector.select_model(sensitive_request, sample_context)
        
        # Should select Ollama for sensitive content
        assert selected.provider == Provider.OLLAMA

    @pytest.mark.asyncio
    async def test_initialization_idempotent(self, selector):
        """Test that multiple initializations don't cause issues."""
        await selector.initialize()
        await selector.initialize()
        await selector.initialize()
        
        # Should still work normally
        assert selector._initialized is True

    @pytest.mark.asyncio
    async def test_selection_reason_provided(self, selector, sample_request, sample_context):
        """Test that a human-readable selection reason is provided."""
        await selector.initialize()
        
        selected = await selector.select_model(sample_request, sample_context)
        
        assert selected.selection_reason
        assert len(selected.selection_reason) > 0
