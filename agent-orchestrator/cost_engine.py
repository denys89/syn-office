"""
Cost Engine for estimating and calculating credit costs.

Maps model execution to credits based on:
- Per-model pricing (from models.yaml)
- Model cost tier (fallback)
- Token usage
- Provider pricing

Phase 2 Enhancement: Uses model registry pricing configuration.
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from model_selection.types import CostLevel, Provider, ModelDefinition, ModelPricing

logger = logging.getLogger(__name__)


@dataclass
class CostEstimate:
    """Estimated cost for a task execution."""
    estimated_credits: int
    model_name: str
    cost_level: CostLevel
    estimated_input_tokens: int
    estimated_output_tokens: int


@dataclass
class ActualCost:
    """Actual cost after task execution."""
    credits: int
    model_name: str
    input_tokens: int
    output_tokens: int
    usd_cost: float  # For reporting


# Fallback credit cost per 1K tokens by cost level (when model has no pricing config)
FALLBACK_CREDITS_PER_1K: Dict[CostLevel, Dict[str, float]] = {
    CostLevel.FREE: {"input": 0.0, "output": 0.0},
    CostLevel.LOW: {"input": 1.0, "output": 2.0},
    CostLevel.MEDIUM: {"input": 5.0, "output": 10.0},
    CostLevel.HIGH: {"input": 25.0, "output": 50.0},
}

# Fallback USD cost per 1K tokens (when model has no pricing config)
FALLBACK_USD_PER_1K: Dict[CostLevel, Dict[str, float]] = {
    CostLevel.FREE: {"input": 0.0, "output": 0.0},
    CostLevel.LOW: {"input": 0.00006, "output": 0.00024},
    CostLevel.MEDIUM: {"input": 0.0005, "output": 0.0015},
    CostLevel.HIGH: {"input": 0.005, "output": 0.015},
}

# Default token estimates for pre-execution cost check
DEFAULT_INPUT_TOKENS = 1000
DEFAULT_OUTPUT_TOKENS = 500


class CostEngine:
    """
    Calculate and estimate credit costs for model executions.
    
    Supports both per-model pricing (from YAML config) and 
    cost-level fallback pricing.
    """
    
    def get_pricing(self, model: ModelDefinition) -> Tuple[float, float]:
        """
        Get credit rates for a model.
        
        Returns:
            Tuple of (credits_per_1k_input, credits_per_1k_output)
        """
        if model.pricing:
            return (
                model.pricing.credits_per_1k_input,
                model.pricing.credits_per_1k_output,
            )
        
        # Fallback to cost level defaults
        rates = FALLBACK_CREDITS_PER_1K.get(
            model.cost_level, 
            FALLBACK_CREDITS_PER_1K[CostLevel.MEDIUM]
        )
        return rates["input"], rates["output"]
    
    def get_usd_rates(self, model: ModelDefinition) -> Tuple[float, float]:
        """
        Get USD rates for a model (for reporting).
        
        Returns:
            Tuple of (usd_per_1k_input, usd_per_1k_output)
        """
        if model.pricing:
            return (
                model.pricing.usd_per_1k_input,
                model.pricing.usd_per_1k_output,
            )
        
        # Fallback to cost level defaults
        rates = FALLBACK_USD_PER_1K.get(
            model.cost_level,
            FALLBACK_USD_PER_1K[CostLevel.MEDIUM]
        )
        return rates["input"], rates["output"]
    
    def estimate_credits_for_model(
        self,
        model: ModelDefinition,
        estimated_input_tokens: int = DEFAULT_INPUT_TOKENS,
        estimated_output_tokens: int = DEFAULT_OUTPUT_TOKENS,
    ) -> int:
        """
        Estimate credits needed before task execution using model's pricing.
        """
        input_rate, output_rate = self.get_pricing(model)
        
        input_credits = (estimated_input_tokens / 1000) * input_rate
        output_credits = (estimated_output_tokens / 1000) * output_rate
        
        # Round up
        total = int(input_credits + output_credits + 0.99)
        
        # Minimum 1 credit for non-free models
        if model.cost_level != CostLevel.FREE and total < 1:
            total = 1
            
        return total
    
    def calculate_credits_for_model(
        self,
        model: ModelDefinition,
        input_tokens: int,
        output_tokens: int,
    ) -> int:
        """
        Calculate actual credits consumed using model's pricing.
        """
        input_rate, output_rate = self.get_pricing(model)
        
        input_credits = (input_tokens / 1000) * input_rate
        output_credits = (output_tokens / 1000) * output_rate
        
        total = round(input_credits + output_credits)
        
        if model.cost_level != CostLevel.FREE and total < 1:
            total = 1
            
        return total
    
    def calculate_usd_for_model(
        self,
        model: ModelDefinition,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate USD cost for a model execution.
        """
        input_rate, output_rate = self.get_usd_rates(model)
        
        input_cost = (input_tokens / 1000) * input_rate
        output_cost = (output_tokens / 1000) * output_rate
        
        return round(input_cost + output_cost, 6)
    
    # === Legacy methods (backward compatibility with Phase 1) ===
    
    def estimate_credits(
        self,
        cost_level: CostLevel,
        estimated_input_tokens: int = DEFAULT_INPUT_TOKENS,
        estimated_output_tokens: int = DEFAULT_OUTPUT_TOKENS,
    ) -> int:
        """Estimate credits using cost level (legacy, for backward compat)."""
        rates = FALLBACK_CREDITS_PER_1K.get(
            cost_level, 
            FALLBACK_CREDITS_PER_1K[CostLevel.MEDIUM]
        )
        
        input_credits = (estimated_input_tokens / 1000) * rates["input"]
        output_credits = (estimated_output_tokens / 1000) * rates["output"]
        
        total = int(input_credits + output_credits + 0.99)
        
        if cost_level != CostLevel.FREE and total < 1:
            total = 1
            
        return total
    
    def calculate_actual_credits(
        self,
        cost_level: CostLevel,
        input_tokens: int,
        output_tokens: int,
    ) -> int:
        """Calculate actual credits using cost level (legacy)."""
        rates = FALLBACK_CREDITS_PER_1K.get(
            cost_level, 
            FALLBACK_CREDITS_PER_1K[CostLevel.MEDIUM]
        )
        
        input_credits = (input_tokens / 1000) * rates["input"]
        output_credits = (output_tokens / 1000) * rates["output"]
        
        total = round(input_credits + output_credits)
        
        if cost_level != CostLevel.FREE and total < 1:
            total = 1
            
        return total
    
    def calculate_usd_cost(
        self,
        cost_level: CostLevel,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate USD cost using cost level (legacy)."""
        rates = FALLBACK_USD_PER_1K.get(
            cost_level, 
            FALLBACK_USD_PER_1K[CostLevel.MEDIUM]
        )
        
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]
        
        return round(input_cost + output_cost, 6)
    
    def get_cost_level_for_model(self, model_name: str, provider: Provider) -> CostLevel:
        """Determine cost level for a model (legacy fallback)."""
        if provider == Provider.OLLAMA:
            return CostLevel.FREE
        if provider == Provider.GROQ:
            return CostLevel.LOW
        
        model_lower = model_name.lower()
        if "gpt-4" in model_lower or "claude-3-opus" in model_lower or "claude-3-5-sonnet" in model_lower:
            return CostLevel.HIGH
        elif "gpt-3.5" in model_lower or "claude-3-sonnet" in model_lower or "claude-3-haiku" in model_lower:
            return CostLevel.MEDIUM
        
        return CostLevel.MEDIUM


# Singleton
_cost_engine: Optional[CostEngine] = None


def get_cost_engine() -> CostEngine:
    """Get the cost engine singleton."""
    global _cost_engine
    if _cost_engine is None:
        _cost_engine = CostEngine()
    return _cost_engine

