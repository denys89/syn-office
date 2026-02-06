"""Tests for Scoring Engine."""

import pytest
from model_selection.scoring_engine import ScoringEngine
from model_selection.types import (
    ModelDefinition,
    ModelCapabilities,
    TaskCapabilityProfile,
    CostLevel,
    LatencyLevel,
    Provider,
)


class TestScoringEngine:
    """Test suite for ScoringEngine."""

    @pytest.fixture
    def scorer(self):
        """Create a fresh scoring engine instance."""
        engine = ScoringEngine()
        engine._loaded = True  # Skip loading config
        return engine

    @pytest.fixture
    def models(self):
        """Create test model definitions."""
        return [
            ModelDefinition(
                name="gpt-4-turbo",
                provider=Provider.OPENAI,
                cost_level=CostLevel.HIGH,
                latency=LatencyLevel.MEDIUM,
                max_tokens=128000,
                capabilities=ModelCapabilities(reasoning=9, coding=9, summarization=8),
            ),
            ModelDefinition(
                name="gpt-3.5-turbo",
                provider=Provider.OPENAI,
                cost_level=CostLevel.LOW,
                latency=LatencyLevel.FAST,
                max_tokens=16000,
                capabilities=ModelCapabilities(reasoning=6, coding=6, summarization=7, speed=9),
            ),
            ModelDefinition(
                name="llama3:8b",
                provider=Provider.OLLAMA,
                cost_level=CostLevel.FREE,
                latency=LatencyLevel.MEDIUM,
                max_tokens=8000,
                capabilities=ModelCapabilities(reasoning=6, coding=6, summarization=6),
            ),
        ]

    def test_score_models_returns_sorted_list(self, scorer, models):
        """Test that scoring returns sorted results."""
        profile = TaskCapabilityProfile(
            required_capabilities={"coding": 0.8},
            min_capability_score=5,
        )
        
        scores = scorer.score_models(models, profile)
        
        assert len(scores) == 3
        # Results should be sorted by (meets_requirements, total_score) descending
        for i in range(len(scores) - 1):
            if scores[i].meets_requirements == scores[i + 1].meets_requirements:
                assert scores[i].total_score >= scores[i + 1].total_score

    def test_high_capability_model_scores_higher(self, scorer, models):
        """Test that models with higher capabilities score higher."""
        profile = TaskCapabilityProfile(
            required_capabilities={"coding": 0.9, "reasoning": 0.8},
            min_capability_score=5,
        )
        
        scores = scorer.score_models(models, profile)
        gpt4_score = next(s for s in scores if s.model_name == "gpt-4-turbo")
        gpt35_score = next(s for s in scores if s.model_name == "gpt-3.5-turbo")
        
        assert gpt4_score.capability_score > gpt35_score.capability_score

    def test_free_model_has_high_cost_score(self, scorer, models):
        """Test that free models get high cost efficiency scores."""
        profile = TaskCapabilityProfile()
        
        scores = scorer.score_models(models, profile)
        llama_score = next(s for s in scores if s.model_name == "llama3:8b")
        gpt4_score = next(s for s in scores if s.model_name == "gpt-4-turbo")
        
        assert llama_score.cost_score > gpt4_score.cost_score

    def test_fast_model_has_high_speed_score(self, scorer, models):
        """Test that fast models get high speed scores."""
        profile = TaskCapabilityProfile()
        
        scores = scorer.score_models(models, profile)
        gpt35_score = next(s for s in scores if s.model_name == "gpt-3.5-turbo")
        gpt4_score = next(s for s in scores if s.model_name == "gpt-4-turbo")
        
        assert gpt35_score.speed_score > gpt4_score.speed_score

    def test_model_disqualified_if_unavailable(self, scorer):
        """Test that unavailable models are disqualified."""
        unavailable_model = ModelDefinition(
            name="unavailable-model",
            provider=Provider.OPENAI,
            cost_level=CostLevel.LOW,
            latency=LatencyLevel.FAST,
            max_tokens=16000,
            available=False,
            capabilities=ModelCapabilities(),
        )
        
        profile = TaskCapabilityProfile()
        scores = scorer.score_models([unavailable_model], profile)
        
        assert scores[0].meets_requirements is False
        assert "not available" in scores[0].disqualification_reason.lower()

    def test_model_disqualified_if_context_insufficient(self, scorer, models):
        """Test that models are disqualified if context length is insufficient."""
        profile = TaskCapabilityProfile(
            context_length_needed=100000,  # Needs 100K context
        )
        
        scores = scorer.score_models(models, profile)
        llama_score = next(s for s in scores if s.model_name == "llama3:8b")
        
        assert llama_score.meets_requirements is False
        assert "context" in llama_score.disqualification_reason.lower()

    def test_model_disqualified_if_requires_local(self, scorer, models):
        """Test that external models are disqualified when local is required."""
        profile = TaskCapabilityProfile(
            requires_local=True,
        )
        
        scores = scorer.score_models(models, profile)
        
        # OpenAI models should be disqualified
        for score in scores:
            if score.provider == Provider.OPENAI:
                assert score.meets_requirements is False
                assert "local" in score.disqualification_reason.lower()

    def test_model_disqualified_if_cost_exceeds_max(self, scorer, models):
        """Test that expensive models are disqualified when cost is limited."""
        profile = TaskCapabilityProfile(
            max_cost_level=CostLevel.LOW,
        )
        
        scores = scorer.score_models(models, profile)
        gpt4_score = next(s for s in scores if s.model_name == "gpt-4-turbo")
        
        assert gpt4_score.meets_requirements is False
        assert "cost" in gpt4_score.disqualification_reason.lower()

    def test_min_capability_score_respected(self, scorer, models):
        """Test that models below minimum capability score don't meet requirements."""
        profile = TaskCapabilityProfile(
            required_capabilities={"coding": 1.0},
            min_capability_score=8,  # High threshold
        )
        
        scores = scorer.score_models(models, profile)
        
        # Only GPT-4 should meet requirements (coding=9)
        gpt4_score = next(s for s in scores if s.model_name == "gpt-4-turbo")
        gpt35_score = next(s for s in scores if s.model_name == "gpt-3.5-turbo")
        
        assert gpt4_score.meets_requirements is True
        assert gpt35_score.meets_requirements is False
