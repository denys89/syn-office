"""Scoring Engine - Calculates model suitability scores based on task requirements."""

import logging
from typing import Dict, List, Optional
from pathlib import Path
import yaml

from .types import (
    ModelDefinition,
    TaskCapabilityProfile,
    ModelScore,
    CostLevel,
    LatencyLevel,
)

logger = logging.getLogger(__name__)

# Default scoring weights
DEFAULT_WEIGHTS = {
    "capability_match": 0.40,
    "speed": 0.20,
    "cost_efficiency": 0.30,
    "reliability": 0.10,
}

# Cost level to score mapping (higher = cheaper = better)
COST_SCORES = {
    CostLevel.FREE: 10.0,
    CostLevel.LOW: 8.0,
    CostLevel.MEDIUM: 5.0,
    CostLevel.HIGH: 2.0,
}

# Latency to speed score mapping
LATENCY_SCORES = {
    LatencyLevel.FAST: 10.0,
    LatencyLevel.MEDIUM: 6.0,
    LatencyLevel.SLOW: 3.0,
}


class ScoringEngine:
    """Calculates weighted suitability scores for models based on task requirements."""

    def __init__(self, policies_path: Optional[str] = None):
        self.policies_path = policies_path or self._default_policies_path()
        self._weights = DEFAULT_WEIGHTS.copy()
        self._loaded = False

    def _default_policies_path(self) -> str:
        """Get default policies path relative to this file."""
        return str(Path(__file__).parent.parent / "config" / "policies.yaml")

    async def load(self) -> None:
        """Load scoring weights from policies config."""
        if self._loaded:
            return

        try:
            with open(self.policies_path, "r") as f:
                config = yaml.safe_load(f)
            
            weights = config.get("policies", {}).get("weights", {})
            if weights:
                self._weights = weights
            self._loaded = True
            logger.debug(f"Loaded scoring weights: {self._weights}")

        except Exception as e:
            logger.warning(f"Could not load policies config: {e}, using defaults")
            self._loaded = True

    def score_models(
        self,
        models: List[ModelDefinition],
        task_profile: TaskCapabilityProfile,
    ) -> List[ModelScore]:
        """
        Score all models against task requirements.
        
        Args:
            models: List of candidate models
            task_profile: Required capabilities for the task
            
        Returns:
            List of ModelScore objects, sorted by total_score descending
        """
        scores = []
        
        for model in models:
            score = self._score_model(model, task_profile)
            scores.append(score)
        
        # Sort by total score (highest first), putting qualified models first
        scores.sort(key=lambda s: (s.meets_requirements, s.total_score), reverse=True)
        
        return scores

    def _score_model(
        self,
        model: ModelDefinition,
        task_profile: TaskCapabilityProfile,
    ) -> ModelScore:
        """Calculate the score for a single model."""
        # Check disqualification conditions first
        disqualification = self._check_disqualification(model, task_profile)
        if disqualification:
            return ModelScore(
                model_name=model.name,
                provider=model.provider,
                total_score=0.0,
                capability_score=0.0,
                speed_score=0.0,
                cost_score=0.0,
                reliability_score=0.0,
                meets_requirements=False,
                disqualification_reason=disqualification,
            )

        # Calculate individual scores
        capability_score = self._calculate_capability_score(model, task_profile)
        speed_score = self._calculate_speed_score(model)
        cost_score = self._calculate_cost_score(model, task_profile)
        reliability_score = self._calculate_reliability_score(model)

        # Weighted total
        total_score = (
            capability_score * self._weights["capability_match"]
            + speed_score * self._weights["speed"]
            + cost_score * self._weights["cost_efficiency"]
            + reliability_score * self._weights["reliability"]
        )

        # Check if meets minimum requirements
        meets_requirements = capability_score >= task_profile.min_capability_score

        return ModelScore(
            model_name=model.name,
            provider=model.provider,
            total_score=total_score,
            capability_score=capability_score,
            speed_score=speed_score,
            cost_score=cost_score,
            reliability_score=reliability_score,
            meets_requirements=meets_requirements,
        )

    def _check_disqualification(
        self,
        model: ModelDefinition,
        task_profile: TaskCapabilityProfile,
    ) -> Optional[str]:
        """Check if a model should be disqualified from selection."""
        # Not available
        if not model.available:
            return "Model is not available"

        # Requires local but model is external
        if task_profile.requires_local and model.provider.value != "ollama":
            return "Task requires local model for sensitive content"

        # Context length insufficient
        if model.max_tokens < task_profile.context_length_needed:
            return f"Insufficient context length ({model.max_tokens} < {task_profile.context_length_needed})"

        # Cost exceeds maximum
        cost_order = [CostLevel.FREE, CostLevel.LOW, CostLevel.MEDIUM, CostLevel.HIGH]
        if cost_order.index(model.cost_level) > cost_order.index(task_profile.max_cost_level):
            return f"Cost level {model.cost_level} exceeds maximum {task_profile.max_cost_level}"

        return None

    def _calculate_capability_score(
        self,
        model: ModelDefinition,
        task_profile: TaskCapabilityProfile,
    ) -> float:
        """Calculate capability match score (0-10)."""
        if not task_profile.required_capabilities:
            # No specific requirements, use average of model capabilities
            caps = model.capabilities
            all_scores = [
                caps.reasoning, caps.coding, caps.summarization,
                caps.planning, caps.structured_output,
            ]
            return sum(all_scores) / len(all_scores)

        total_weighted_score = 0.0
        total_weight = 0.0

        for capability, weight in task_profile.required_capabilities.items():
            model_score = getattr(model.capabilities, capability, 5)
            total_weighted_score += model_score * weight
            total_weight += weight

        if total_weight == 0:
            return 5.0

        return total_weighted_score / total_weight

    def _calculate_speed_score(self, model: ModelDefinition) -> float:
        """Calculate speed score based on latency (0-10)."""
        return LATENCY_SCORES.get(model.latency, 5.0)

    def _calculate_cost_score(
        self,
        model: ModelDefinition,
        task_profile: TaskCapabilityProfile,
    ) -> float:
        """Calculate cost efficiency score (0-10)."""
        return COST_SCORES.get(model.cost_level, 5.0)

    def _calculate_reliability_score(self, model: ModelDefinition) -> float:
        """
        Calculate reliability score (0-10).
        
        In MVP, this is based on provider reputation.
        Future: Use historical success rate from metrics.
        """
        # Provider-based reliability estimates
        reliability_by_provider = {
            "openai": 9.0,
            "anthropic": 9.0,
            "groq": 7.0,
            "ollama": 6.0,  # Local, depends on hardware
        }
        return reliability_by_provider.get(model.provider.value, 5.0)


# Singleton instance
_engine: Optional[ScoringEngine] = None


def get_scoring_engine() -> ScoringEngine:
    """Get the scoring engine singleton."""
    global _engine
    if _engine is None:
        _engine = ScoringEngine()
    return _engine
