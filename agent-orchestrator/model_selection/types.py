"""Model Selection Engine types and data models."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime


class CostLevel(str, Enum):
    """Cost tier for models."""
    FREE = "free"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LatencyLevel(str, Enum):
    """Latency tier for models."""
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


class Provider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"


class ModelCapabilities(BaseModel):
    """Capability scores for a model (0-10 scale)."""
    reasoning: int = 5
    coding: int = 5
    long_context: int = 5
    summarization: int = 5
    planning: int = 5
    structured_output: int = 5
    multimodal: int = 0
    speed: int = 5
    web_search: int = 0
    real_time_data: int = 0


class ModelDefinition(BaseModel):
    """Definition of a model from the registry."""
    name: str
    provider: Provider
    cost_level: CostLevel
    latency: LatencyLevel
    max_tokens: int
    available: bool = True
    capabilities: ModelCapabilities


class TaskCapabilityProfile(BaseModel):
    """Required capabilities for a specific task."""
    required_capabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Capability name -> importance weight (0.0-1.0)"
    )
    min_capability_score: int = 5
    max_cost_level: CostLevel = CostLevel.HIGH
    requires_local: bool = False
    context_length_needed: int = 4000
    agent_role: Optional[str] = None


class ModelScore(BaseModel):
    """Scoring result for a model."""
    model_name: str
    provider: Provider
    total_score: float
    capability_score: float
    speed_score: float
    cost_score: float
    reliability_score: float
    meets_requirements: bool
    disqualification_reason: Optional[str] = None


class SelectedModel(BaseModel):
    """Result of model selection."""
    model_name: str
    provider: Provider
    score: float
    alternatives: List[str] = Field(default_factory=list)
    selection_reason: str
    task_profile: TaskCapabilityProfile


class ModelExecutionMetrics(BaseModel):
    """Metrics for a model execution (for observability)."""
    id: Optional[str] = None
    task_id: str
    agent_id: str
    selected_model: str
    provider: str
    alternatives_considered: List[str] = Field(default_factory=list)
    capability_match_score: float
    total_score: float
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    success: bool
    error: Optional[str] = None
    fallback_used: bool = False
    fallback_model: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GenerationRequest(BaseModel):
    """Request to generate a response from an LLM."""
    model_name: str
    provider: Provider
    messages: List[Dict[str, str]]
    max_tokens: int = 2000
    temperature: float = 0.7


class GenerationResponse(BaseModel):
    """Response from LLM generation."""
    content: str
    model_name: str
    provider: Provider
    token_usage: Dict[str, int]
    latency_ms: int
