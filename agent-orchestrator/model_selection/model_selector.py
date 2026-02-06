"""Model Selector - Main orchestration class for model selection and execution."""

import logging
import time
from typing import Dict, List, Optional, Tuple

from models import ExecuteRequest, AgentContext
from .types import (
    ModelDefinition,
    TaskCapabilityProfile,
    SelectedModel,
    ModelScore,
    ModelExecutionMetrics,
    Provider,
)
from .model_registry import ModelRegistry, get_model_registry
from .capability_extractor import CapabilityExtractor, get_capability_extractor
from .scoring_engine import ScoringEngine, get_scoring_engine
from .policy_enforcer import PolicyEnforcer, get_policy_enforcer

logger = logging.getLogger(__name__)


class ModelSelector:
    """
    Main orchestrator for model selection.
    
    Coordinates capability extraction, scoring, policy enforcement,
    and provides fallback logic for execution failures.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        extractor: Optional[CapabilityExtractor] = None,
        scorer: Optional[ScoringEngine] = None,
        enforcer: Optional[PolicyEnforcer] = None,
    ):
        self.registry = registry or get_model_registry()
        self.extractor = extractor or get_capability_extractor()
        self.scorer = scorer or get_scoring_engine()
        self.enforcer = enforcer or get_policy_enforcer()
        self._initialized = False
        self._providers: Dict[str, "BaseModelProvider"] = {}

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return

        await self.registry.load()
        await self.extractor.load()
        await self.scorer.load()
        await self.enforcer.load()
        
        # Initialize providers
        await self._init_providers()
        
        self._initialized = True
        logger.info("Model selector initialized")

    async def _init_providers(self) -> None:
        """Initialize model providers."""
        from providers import (
            OpenAIProvider,
            AnthropicProvider,
            GroqProvider,
            OllamaProvider,
            get_provider_for,
        )
        
        # Providers are lazy-loaded via get_provider_for()
        logger.debug("Provider initialization deferred to first use")

    async def select_model(
        self,
        request: ExecuteRequest,
        context: AgentContext,
    ) -> SelectedModel:
        """
        Select the optimal model for a task.
        
        Args:
            request: The execution request
            context: Agent context with role and history
            
        Returns:
            SelectedModel with the chosen model and alternatives
        """
        await self.initialize()

        # Extract capability requirements
        task_profile = self.extractor.extract(
            user_input=request.input,
            agent_role=context.agent_role,
            context_length=self._estimate_context_length(context),
        )
        logger.debug(f"Task profile: {task_profile.required_capabilities}")

        # Get available models
        models = self.registry.get_available_models()
        if not models:
            raise ValueError("No models available in registry")

        # Score all models
        scores = self.scorer.score_models(models, task_profile)

        # Apply policy constraints
        model_map = {m.name: m for m in models}
        filtered_scores = self.enforcer.filter_by_policy(
            scores, model_map, request.input
        )

        # Select best model
        if not filtered_scores or not filtered_scores[0].meets_requirements:
            # No suitable model found, fall back to default
            default = self.registry.get_default_model()
            if default:
                return SelectedModel(
                    model_name=default.name,
                    provider=default.provider,
                    score=0.0,
                    alternatives=[],
                    selection_reason="Fallback to default model (no suitable match)",
                    task_profile=task_profile,
                )
            raise ValueError("No suitable model found and no default available")

        best = filtered_scores[0]
        alternatives = [s.model_name for s in filtered_scores[1:5]]  # Top 4 alternatives

        return SelectedModel(
            model_name=best.model_name,
            provider=best.provider,
            score=best.total_score,
            alternatives=alternatives,
            selection_reason=self._build_selection_reason(best, task_profile),
            task_profile=task_profile,
        )

    async def execute_with_fallback(
        self,
        selected: SelectedModel,
        context: AgentContext,
        user_input: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Tuple[str, Dict, ModelExecutionMetrics]:
        """
        Execute generation with automatic fallback on failure.
        
        Returns:
            Tuple of (response_content, token_usage, execution_metrics)
        """
        from providers import get_provider_for

        models_tried = []
        candidates = [selected.model_name] + selected.alternatives
        max_retries = self.enforcer.get_max_retries()
        fallback_enabled = self.enforcer.get_fallback_enabled()

        for attempt, model_name in enumerate(candidates):
            if attempt > 0 and not fallback_enabled:
                break

            model = self.registry.get_model(model_name)
            if not model:
                continue

            models_tried.append(model_name)
            
            try:
                provider = await get_provider_for(model.provider)
                if not provider:
                    logger.warning(f"Provider {model.provider} not available")
                    continue

                # Check provider health
                if not await provider.health_check():
                    logger.warning(f"Provider {model.provider} health check failed")
                    continue

                # Build messages
                messages = self._build_messages(context, user_input)

                # Execute
                start_time = time.time()
                content, token_usage = await provider.generate(
                    model_name=model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                latency_ms = int((time.time() - start_time) * 1000)

                # Build metrics
                metrics = ModelExecutionMetrics(
                    task_id="",  # Set by caller
                    agent_id=context.agent_id,
                    selected_model=model_name,
                    provider=model.provider.value,
                    alternatives_considered=selected.alternatives,
                    capability_match_score=selected.score,
                    total_score=selected.score,
                    latency_ms=latency_ms,
                    prompt_tokens=token_usage.get("prompt_tokens", 0),
                    completion_tokens=token_usage.get("completion_tokens", 0),
                    total_tokens=token_usage.get("total_tokens", 0),
                    estimated_cost=self.enforcer.get_cost_estimate(
                        model.cost_level,
                        token_usage.get("total_tokens", 0),
                    ),
                    success=True,
                    fallback_used=attempt > 0,
                    fallback_model=model_name if attempt > 0 else None,
                )

                logger.info(f"Model {model_name} executed successfully in {latency_ms}ms")
                return content, token_usage, metrics

            except Exception as e:
                logger.error(f"Model {model_name} failed: {e}")
                if attempt >= max_retries:
                    # Create failure metrics
                    metrics = ModelExecutionMetrics(
                        task_id="",
                        agent_id=context.agent_id,
                        selected_model=model_name,
                        provider=model.provider.value,
                        alternatives_considered=selected.alternatives,
                        capability_match_score=selected.score,
                        total_score=selected.score,
                        latency_ms=0,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        estimated_cost=0,
                        success=False,
                        error=str(e),
                        fallback_used=attempt > 0,
                    )
                    raise RuntimeError(f"All models failed. Tried: {models_tried}") from e

        raise RuntimeError("No models could complete the request")

    def _estimate_context_length(self, context: AgentContext) -> int:
        """Estimate the context length needed."""
        base_length = len(context.system_prompt) // 4  # Rough token estimate
        history_length = sum(
            len(str(msg.get("content", ""))) // 4
            for msg in context.conversation_history[-10:]
        )
        memory_length = sum(len(m) // 4 for m in context.memories)
        return base_length + history_length + memory_length + 500  # Buffer

    def _build_selection_reason(
        self,
        score: ModelScore,
        profile: TaskCapabilityProfile,
    ) -> str:
        """Build a human-readable selection reason."""
        parts = [f"Score: {score.total_score:.2f}"]
        
        if profile.required_capabilities:
            caps = list(profile.required_capabilities.keys())[:3]
            parts.append(f"Matched: {', '.join(caps)}")
        
        parts.append(f"Provider: {score.provider.value}")
        
        return " | ".join(parts)

    def _build_messages(
        self,
        context: AgentContext,
        user_input: str,
    ) -> List[Dict[str, str]]:
        """Build messages array for LLM."""
        messages = []

        # System prompt
        system_content = self._build_system_prompt(context)
        messages.append({"role": "system", "content": system_content})

        # Conversation history
        for msg in context.conversation_history[-10:]:
            messages.append({
                "role": "user" if msg.get("sender_type") == "user" else "assistant",
                "content": msg.get("content", ""),
            })

        # Current input
        messages.append({"role": "user", "content": user_input})

        return messages

    def _build_system_prompt(self, context: AgentContext) -> str:
        """Build system prompt with context."""
        parts = [
            context.system_prompt,
            "",
            "IMPORTANT GUIDELINES:",
            "- You are part of Synoffice, an AI-native digital office.",
            "- Respond professionally and helpfully.",
            "- Stay within your role and expertise.",
            "",
        ]

        if context.memories:
            parts.extend([
                "RELEVANT MEMORIES:",
                *[f"- {memory}" for memory in context.memories],
                "",
            ])

        return "\n".join(parts)


# Singleton instance
_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """Get the model selector singleton."""
    global _selector
    if _selector is None:
        _selector = ModelSelector()
    return _selector
