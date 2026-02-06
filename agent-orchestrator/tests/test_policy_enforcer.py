"""Tests for Policy Enforcer."""

import pytest
from model_selection.policy_enforcer import PolicyEnforcer
from model_selection.types import (
    ModelDefinition,
    ModelCapabilities,
    ModelScore,
    CostLevel,
    LatencyLevel,
    Provider,
)


class TestPolicyEnforcer:
    """Test suite for PolicyEnforcer."""

    @pytest.fixture
    def enforcer(self):
        """Create a fresh policy enforcer instance."""
        enf = PolicyEnforcer()
        enf._loaded = True
        enf._policies = {
            "prefer_local": True,
            "local_capability_threshold": 6,
            "fallback_enabled": True,
            "max_retries": 2,
        }
        enf._restricted_patterns = [
            {"pattern": "confidential|secret", "allowed_providers": ["ollama"]},
        ]
        enf._provider_priority = ["ollama", "groq", "openai", "anthropic"]
        enf._cost_levels = {"free": 0, "low": 0.001, "medium": 0.01, "high": 0.03}
        return enf

    @pytest.fixture
    def models(self):
        """Create test model definitions."""
        return {
            "gpt-4-turbo": ModelDefinition(
                name="gpt-4-turbo",
                provider=Provider.OPENAI,
                cost_level=CostLevel.HIGH,
                latency=LatencyLevel.MEDIUM,
                max_tokens=128000,
                capabilities=ModelCapabilities(reasoning=9, coding=9),
            ),
            "llama3:8b": ModelDefinition(
                name="llama3:8b",
                provider=Provider.OLLAMA,
                cost_level=CostLevel.FREE,
                latency=LatencyLevel.MEDIUM,
                max_tokens=8000,
                capabilities=ModelCapabilities(reasoning=6, coding=6),
            ),
        }

    @pytest.fixture
    def scores(self):
        """Create test model scores."""
        return [
            ModelScore(
                model_name="gpt-4-turbo",
                provider=Provider.OPENAI,
                total_score=8.0,
                capability_score=9.0,
                speed_score=6.0,
                cost_score=2.0,
                reliability_score=9.0,
                meets_requirements=True,
            ),
            ModelScore(
                model_name="llama3:8b",
                provider=Provider.OLLAMA,
                total_score=6.0,
                capability_score=6.0,
                speed_score=6.0,
                cost_score=10.0,
                reliability_score=6.0,
                meets_requirements=True,
            ),
        ]

    def test_restriction_filters_external_providers(self, enforcer, scores, models):
        """Test that restricted patterns filter out external providers."""
        filtered = enforcer.filter_by_policy(
            scores=scores,
            models=models,
            user_input="This is confidential information",
        )
        
        # Only Ollama should remain
        assert len(filtered) == 1
        assert filtered[0].provider == Provider.OLLAMA

    def test_no_restriction_keeps_all_providers(self, enforcer, scores, models):
        """Test that normal content keeps all providers."""
        filtered = enforcer.filter_by_policy(
            scores=scores,
            models=models,
            user_input="Write a hello world program",
        )
        
        assert len(filtered) == 2

    def test_local_preference_boosts_ollama(self, enforcer, scores, models):
        """Test that local models get boosted when preference is enabled."""
        filtered = enforcer.filter_by_policy(
            scores=scores,
            models=models,
            user_input="Simple task",
        )
        
        # Find Ollama score
        ollama_score = next(s for s in filtered if s.model_name == "llama3:8b")
        
        # Should be boosted above original 6.0
        assert ollama_score.total_score > 6.0

    def test_provider_priority_affects_ordering(self, enforcer, scores, models):
        """Test that provider priority affects final ordering."""
        # Make scores equal
        equal_scores = [
            ModelScore(
                model_name="gpt-4-turbo",
                provider=Provider.OPENAI,
                total_score=7.0,
                capability_score=7.0,
                speed_score=7.0,
                cost_score=7.0,
                reliability_score=7.0,
                meets_requirements=True,
            ),
            ModelScore(
                model_name="llama3:8b",
                provider=Provider.OLLAMA,
                total_score=7.0,
                capability_score=7.0,
                speed_score=7.0,
                cost_score=7.0,
                reliability_score=7.0,
                meets_requirements=True,
            ),
        ]
        
        filtered = enforcer.filter_by_policy(
            scores=equal_scores,
            models=models,
            user_input="Task",
        )
        
        # Ollama should come first due to priority
        # (Note: local preference boost will also help here)
        assert filtered[0].provider == Provider.OLLAMA

    def test_fallback_enabled_flag(self, enforcer):
        """Test fallback enabled getter."""
        assert enforcer.get_fallback_enabled() is True
        
        enforcer._policies["fallback_enabled"] = False
        assert enforcer.get_fallback_enabled() is False

    def test_max_retries(self, enforcer):
        """Test max retries getter."""
        assert enforcer.get_max_retries() == 2

    def test_cost_estimate_calculation(self, enforcer):
        """Test cost estimation."""
        # 1000 tokens at high cost (0.03 per 1K)
        cost = enforcer.get_cost_estimate(CostLevel.HIGH, 1000)
        assert cost == pytest.approx(0.03)
        
        # 2000 tokens at low cost (0.001 per 1K)
        cost = enforcer.get_cost_estimate(CostLevel.LOW, 2000)
        assert cost == pytest.approx(0.002)
        
        # Free tier
        cost = enforcer.get_cost_estimate(CostLevel.FREE, 1000)
        assert cost == 0
