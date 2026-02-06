"""Policy Enforcer - Applies organizational and cost constraints to model selection."""

import logging
import re
from typing import Dict, List, Optional, Set
from pathlib import Path
import yaml

from .types import (
    ModelDefinition,
    ModelScore,
    TaskCapabilityProfile,
    Provider,
    CostLevel,
)

logger = logging.getLogger(__name__)


class PolicyEnforcer:
    """Applies policy constraints before final model selection."""

    def __init__(self, policies_path: Optional[str] = None):
        self.policies_path = policies_path or self._default_policies_path()
        self._policies: Dict = {}
        self._restricted_patterns: List[Dict] = []
        self._provider_priority: List[str] = []
        self._cost_levels: Dict[str, float] = {}
        self._loaded = False

    def _default_policies_path(self) -> str:
        """Get default policies path relative to this file."""
        return str(Path(__file__).parent.parent / "config" / "policies.yaml")

    async def load(self) -> None:
        """Load policy configuration."""
        if self._loaded:
            return

        try:
            with open(self.policies_path, "r") as f:
                config = yaml.safe_load(f)

            self._policies = config.get("policies", {})
            self._restricted_patterns = config.get("restricted_patterns", [])
            self._provider_priority = config.get("provider_priority", [])
            self._cost_levels = config.get("cost_levels", {})
            self._loaded = True
            logger.debug(f"Loaded policies: prefer_local={self._policies.get('prefer_local')}")

        except Exception as e:
            logger.warning(f"Could not load policies config: {e}, using defaults")
            self._policies = {"prefer_local": True, "fallback_enabled": True}
            self._provider_priority = ["ollama", "groq", "openai", "anthropic"]
            self._loaded = True

    def filter_by_policy(
        self,
        scores: List[ModelScore],
        models: Dict[str, ModelDefinition],
        user_input: str,
    ) -> List[ModelScore]:
        """
        Filter and re-rank models based on policy constraints.
        
        Args:
            scores: Pre-scored model list
            models: Model name -> ModelDefinition map
            user_input: Original user input (for restriction matching)
            
        Returns:
            Filtered and re-ranked list of model scores
        """
        filtered = scores.copy()

        # Apply restriction patterns
        allowed_providers = self._check_restrictions(user_input)
        if allowed_providers:
            filtered = [
                s for s in filtered
                if s.provider.value in allowed_providers
            ]
            logger.info(f"Restricted to providers: {allowed_providers}")

        # Apply local preference
        if self._policies.get("prefer_local", False):
            threshold = self._policies.get("local_capability_threshold", 6)
            filtered = self._apply_local_preference(filtered, models, threshold)

        # Apply provider priority for tie-breaking
        if self._provider_priority:
            filtered = self._apply_provider_priority(filtered)

        return filtered

    def _check_restrictions(self, user_input: str) -> Optional[Set[str]]:
        """Check if any restriction patterns match the input."""
        text_lower = user_input.lower()
        
        for restriction in self._restricted_patterns:
            pattern = restriction.get("pattern", "")
            if re.search(pattern, text_lower, re.IGNORECASE):
                allowed = restriction.get("allowed_providers", [])
                reason = restriction.get("reason", "Policy restriction")
                logger.info(f"Restriction matched: {reason}")
                return set(allowed)
        
        return None

    def _apply_local_preference(
        self,
        scores: List[ModelScore],
        models: Dict[str, ModelDefinition],
        threshold: int,
    ) -> List[ModelScore]:
        """Boost local models if they meet capability threshold."""
        result = []
        
        for score in scores:
            model = models.get(score.model_name)
            if model and model.provider == Provider.OLLAMA:
                # Check if local model meets threshold
                if score.capability_score >= threshold:
                    # Boost score slightly to prefer local
                    boosted = ModelScore(
                        model_name=score.model_name,
                        provider=score.provider,
                        total_score=score.total_score + 0.5,  # Small boost
                        capability_score=score.capability_score,
                        speed_score=score.speed_score,
                        cost_score=score.cost_score,
                        reliability_score=score.reliability_score,
                        meets_requirements=score.meets_requirements,
                        disqualification_reason=score.disqualification_reason,
                    )
                    result.append(boosted)
                else:
                    result.append(score)
            else:
                result.append(score)
        
        # Re-sort after boosting
        result.sort(key=lambda s: (s.meets_requirements, s.total_score), reverse=True)
        return result

    def _apply_provider_priority(self, scores: List[ModelScore]) -> List[ModelScore]:
        """Apply provider priority for tie-breaking."""
        if not self._provider_priority:
            return scores

        def sort_key(score: ModelScore):
            try:
                priority = self._provider_priority.index(score.provider.value)
            except ValueError:
                priority = 999
            return (score.meets_requirements, score.total_score, -priority)

        return sorted(scores, key=sort_key, reverse=True)

    def get_fallback_enabled(self) -> bool:
        """Check if fallback is enabled."""
        return self._policies.get("fallback_enabled", True)

    def get_max_retries(self) -> int:
        """Get maximum retry count."""
        return self._policies.get("max_retries", 2)

    def get_cost_estimate(self, cost_level: CostLevel, tokens: int) -> float:
        """Estimate cost for a model execution."""
        cost_per_1k = self._cost_levels.get(cost_level.value, 0.01)
        return (tokens / 1000) * cost_per_1k


# Singleton instance
_enforcer: Optional[PolicyEnforcer] = None


def get_policy_enforcer() -> PolicyEnforcer:
    """Get the policy enforcer singleton."""
    global _enforcer
    if _enforcer is None:
        _enforcer = PolicyEnforcer()
    return _enforcer
