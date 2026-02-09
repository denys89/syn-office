"""
Main orchestrator for agent task execution.

Enhanced with Model Capability & Selection Engine for dynamic multi-model routing.
Integrated with Credit System for monetization.
"""

import logging
from typing import Optional
import httpx

from config import get_settings
from models import ExecuteRequest, ExecuteResponse, TaskStatus, AgentContext
from database import get_database
from model_selection import get_model_selector, ModelSelector
from model_selection.types import CostLevel
from metrics import get_metrics_service, MetricsService
from credit_client import get_credit_client, CreditClient
from cost_engine import get_cost_engine, CostEngine
from rate_limiter import (
    get_rate_limiter, get_anomaly_detector, get_circuit_breaker,
    CreditRateLimiter, AnomalyDetector, CircuitBreaker, RateLimitAction
)
from tool_execution import (
    get_execution_orchestrator, 
    ExecutionOrchestrator,
    ActionPlan,
    ExecutionResult,
    ExecutionContext,
    PermissionScope
)

logger = logging.getLogger(__name__)

# Lazy import to avoid startup failures if Qdrant is not available
_qdrant_client = None
_qdrant_available = True


async def _get_qdrant():
    """Get Qdrant client with lazy initialization and error handling."""
    global _qdrant_client, _qdrant_available
    
    if not _qdrant_available:
        return None
    
    if _qdrant_client is None:
        try:
            from qdrant_service import get_qdrant_client
            _qdrant_client = await get_qdrant_client()
        except Exception as e:
            logger.warning(f"Qdrant not available, using PostgreSQL-only memory: {e}")
            _qdrant_available = False
            return None
    
    return _qdrant_client


from tool_execution import (
    get_execution_orchestrator, 
    ExecutionOrchestrator,
    ActionPlan,
    ExecutionResult,
    ExecutionContext,
    PermissionScope
)

class Orchestrator:
    """
    Main orchestrator for agent task execution.
    
    Enhanced with Model Capability & Selection Engine for:
    - Dynamic model selection based on task requirements
    - Multi-provider support (OpenAI, Anthropic, Groq, Ollama)
    - Automatic fallback on failures
    - Execution metrics persistence
    
    Integrated with Credit System for:
    - Pre-execution balance checks
    - Credit consumption based on model usage
    - Cost tracking and reporting
    
    Integrated with Tool Execution Layer for:
    - Deterministic tool execution
    - Sequential and parallel action plans
    - Secure, sandboxed execution with permission checks
    """
    
    def __init__(self):
        self.db = get_database()
        self.settings = get_settings()
        self.model_selector: ModelSelector = get_model_selector()
        self.metrics: MetricsService = get_metrics_service()
        self.credit_client: CreditClient = get_credit_client()
        self.cost_engine: CostEngine = get_cost_engine()
        self.rate_limiter: CreditRateLimiter = get_rate_limiter()
        self.anomaly_detector: AnomalyDetector = get_anomaly_detector()
        self.circuit_breaker: CircuitBreaker = get_circuit_breaker()
        self.tool_orchestrator: Optional[ExecutionOrchestrator] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the orchestrator and its dependencies."""
        if self._initialized:
            return
        
        # Initialize model selector
        await self.model_selector.initialize()
        
        # Initialize tool execution layer
        self.tool_orchestrator = await get_execution_orchestrator()
        
        # Initialize metrics with database pool
        if self.db.pool:
            await self.metrics.initialize(self.db.pool)
        
        self._initialized = True
        logger.info("Orchestrator initialized with model selection, credit system, and tool execution layer")

    # ... [existing methods] ...

    async def execute_tool_plan(
        self, 
        plan: ActionPlan, 
        user_id: str, 
        office_id: str
    ) -> ExecutionResult:
        """
        Execute a tool action plan.
        
        Args:
            plan: The action plan to execute
            user_id: The ID of the user requesting execution
            office_id: The office context
            
        Returns:
            ExecutionResult containing outputs and status
        """
        await self.initialize()
        
        # user_id and office_id validation/loading could happen here
        # For now, we assume authenticated context passed from API layer
        
        # Build execution context
        # In a real scenario, we would fetch permissions from the DB
        # For MVP/testing, we might construct a context with ample permissions 
        # or fetch from a user_permissions table.
        # Here we'll Mock it or fetch it. 
        # TODO: integrated permission fetching. 
        # For now, we'll create a context based on the passed IDs and assume 
        # the SecurityGateway will validate against specific scopes if we populate them.
        
        # Fetch user permissions (Mock implementation for now)
        # In production: permissions = await self.db.get_user_permissions(user_id)
        permissions = PermissionScope(
            user_id=user_id,
            office_id=office_id,
            granted_scopes=["*"], # TODO: Replace with actual scope loading
            oauth_tokens={}, # TODO: Load tokens from secure storage
        )
        
        context = ExecutionContext(
            user_id=user_id,
            office_id=office_id,
            permissions=permissions
        )
        
        return await self.tool_orchestrator.execute_plan(plan, context)

    
    async def execute_task(self, request: ExecuteRequest) -> ExecuteResponse:
        """
        Execute a task by:
        1. Loading agent context (with semantic memory search)
        2. Estimating and checking credit balance
        3. Selecting optimal model based on task requirements
        4. Generating LLM response with fallback support
        5. Consuming credits based on actual usage
        6. Saving response and updating task
        7. Persisting execution metrics
        """
        credits_consumed = 0
        selected_model_name = ""
        
        try:
            # Ensure initialized
            await self.initialize()
            
            # Update status to thinking
            await self.db.update_task_status(request.task_id, TaskStatus.THINKING.value)
            
            # Load agent context
            context = await self._load_agent_context(request)
            if context is None:
                return ExecuteResponse(
                    task_id=request.task_id,
                    status=TaskStatus.FAILED,
                    error="Agent not found",
                )
            
            # Update status to working
            await self.db.update_task_status(request.task_id, TaskStatus.WORKING.value)
            
            # Select optimal model for this task
            selected = await self.model_selector.select_model(request, context)
            selected_model_name = selected.model_name
            logger.info(
                f"Selected model: {selected.model_name} ({selected.provider}) "
                f"for agent {context.agent_role} | Score: {selected.score:.2f}"
            )
            
            # Get model definition for pricing
            model_def = self.model_selector.registry.get_model(selected.model_name)
            
            # Estimate credits needed using per-model pricing
            if model_def:
                estimated_credits = self.cost_engine.estimate_credits_for_model(model_def)
                is_free_model = model_def.cost_level == CostLevel.FREE
            else:
                # Fallback to cost level
                cost_level = self.cost_engine.get_cost_level_for_model(
                    selected.model_name, selected.provider
                )
                estimated_credits = self.cost_engine.estimate_credits(cost_level)
                is_free_model = cost_level == CostLevel.FREE
            
            # Log local model usage for optimization tracking
            if is_free_model:
                logger.info(f"Using FREE local model: {selected.model_name} (0 credits)")
            
            # Check if office has sufficient credits (skip for free models)
            if not is_free_model:
                credit_check = await self.credit_client.check_balance(
                    request.office_id, estimated_credits
                )
                
                if not credit_check.has_sufficient and not credit_check.error:
                    logger.warning(
                        f"Insufficient credits for task {request.task_id}: "
                        f"has {credit_check.current_balance}, needs {estimated_credits}"
                    )
                    await self.db.update_task_status(
                        request.task_id, 
                        TaskStatus.FAILED.value, 
                        error=f"Insufficient credits: {credit_check.current_balance} available, {estimated_credits} required"
                    )
                    return ExecuteResponse(
                        task_id=request.task_id,
                        status=TaskStatus.FAILED,
                        error=f"Insufficient credits: {credit_check.current_balance} available, {estimated_credits} required",
                    )
                
                # Rate limiting: Check hourly/daily budget limits
                budget_result = await self.rate_limiter.check_budget(
                    office_id=request.office_id,
                    estimated_credits=estimated_credits,
                    credits_remaining=credit_check.current_balance,
                )
                
                if not budget_result.allowed:
                    logger.warning(
                        f"Rate limit blocked task {request.task_id}: {budget_result.reason}"
                    )
                    await self.db.update_task_status(
                        request.task_id,
                        TaskStatus.FAILED.value,
                        error=f"Rate limit: {budget_result.reason}"
                    )
                    return ExecuteResponse(
                        task_id=request.task_id,
                        status=TaskStatus.FAILED,
                        error=f"Rate limit exceeded: {budget_result.reason}",
                    )
                
                if budget_result.action == RateLimitAction.WARN:
                    logger.warning(f"Rate limit warning for {request.office_id}: {budget_result.reason}")
                
                # Anomaly detection: Check for excessive single-task cost
                task_ok, anomaly_reason = await self.anomaly_detector.check_task_credits(
                    request.office_id, estimated_credits
                )
                if not task_ok:
                    logger.warning(f"Anomaly detected for task {request.task_id}: {anomaly_reason}")
                    await self.db.update_task_status(
                        request.task_id,
                        TaskStatus.FAILED.value,
                        error=anomaly_reason
                    )
                    return ExecuteResponse(
                        task_id=request.task_id,
                        status=TaskStatus.FAILED,
                        error=anomaly_reason,
                    )
            
            # Circuit breaker: Check if provider is available
            provider_ok, cb_reason = await self.circuit_breaker.can_execute(selected.provider)
            if not provider_ok:
                logger.warning(f"Circuit breaker open for {selected.provider}: {cb_reason}")
                # Try fallback provider selection
                # For now, just fail - could implement provider-specific fallback here
                await self.db.update_task_status(
                    request.task_id,
                    TaskStatus.FAILED.value,
                    error=cb_reason
                )
                return ExecuteResponse(
                    task_id=request.task_id,
                    status=TaskStatus.FAILED,
                    error=cb_reason,
                )
            
            # Generate response with fallback support
            output, token_usage, metrics = await self.model_selector.execute_with_fallback(
                selected=selected,
                context=context,
                user_input=request.input,
            )
            
            # Calculate actual credits using per-model pricing
            input_tokens = token_usage.get("prompt_tokens", 0)
            output_tokens = token_usage.get("completion_tokens", 0)
            
            if model_def:
                credits_consumed = self.cost_engine.calculate_credits_for_model(
                    model_def, input_tokens, output_tokens
                )
            else:
                credits_consumed = self.cost_engine.calculate_actual_credits(
                    cost_level, input_tokens, output_tokens
                )
            
            # Consume credits (only if non-zero)
            if credits_consumed > 0:
                consume_result = await self.credit_client.consume_credits(
                    office_id=request.office_id,
                    task_id=request.task_id,
                    credits=credits_consumed,
                    model_name=selected.model_name,
                )
                if not consume_result.success:
                    logger.warning(f"Credit consumption failed: {consume_result.error}")
                else:
                    logger.info(
                        f"Consumed {credits_consumed} credits for task {request.task_id} "
                        f"(balance: {consume_result.new_balance})"
                    )
                    # Record for rate limiting
                    await self.rate_limiter.record_consumption(
                        office_id=request.office_id,
                        credits=credits_consumed,
                        model_name=selected.model_name,
                        task_id=request.task_id,
                    )
            
            # Update task with output
            await self.db.update_task_status(
                request.task_id, 
                TaskStatus.DONE.value, 
                output=output
            )
            
            # Save response as agent message
            await self._save_agent_response(request, output)
            
            # Broadcast to WebSocket (via backend)
            await self._notify_backend(request, output)
            
            # Persist execution metrics
            metrics.task_id = request.task_id
            await self.metrics.save(metrics)
            
            # Record circuit breaker success
            await self.circuit_breaker.record_success(selected.provider)
            
            return ExecuteResponse(
                task_id=request.task_id,
                status=TaskStatus.DONE,
                output=output,
                token_usage=token_usage,
            )
            
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            
            # Record circuit breaker failure if we had a selected model
            if selected_model_name:
                try:
                    selected = self.model_selector.registry.get_model(selected_model_name)
                    if selected:
                        await self.circuit_breaker.record_failure(selected.provider)
                except Exception:
                    pass  # Don't fail on metric recording
            
            await self.db.update_task_status(
                request.task_id, 
                TaskStatus.FAILED.value, 
                error=str(e)
            )
            return ExecuteResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
            )
    
    async def _load_agent_context(self, request: ExecuteRequest) -> Optional[AgentContext]:
        """Load full agent context for LLM, including semantic memory search."""
        # Get agent info
        agent = await self.db.get_agent(request.agent_id)
        if not agent:
            return None
        
        # Get conversation history
        history = await self.db.get_conversation_history(request.conversation_id)
        
        # Get memories - try semantic search first, fall back to PostgreSQL
        memories = await self._get_relevant_memories(request.agent_id, request.input)
        
        # Determine name and prompt
        agent_name = agent.get("custom_name") or agent.get("template_name", "Agent")
        system_prompt = agent.get("custom_system_prompt") or agent.get("template_system_prompt", "")
        
        return AgentContext(
            agent_id=request.agent_id,
            agent_name=agent_name,
            agent_role=agent.get("template_role", "Assistant"),
            system_prompt=system_prompt,
            conversation_history=history,
            memories=memories,
        )
    
    async def _get_relevant_memories(self, agent_id: str, query: str) -> list[str]:
        """
        Get relevant memories using semantic search if available,
        otherwise fall back to PostgreSQL key-value memories.
        """
        # Try Qdrant semantic search first
        qdrant = await _get_qdrant()
        if qdrant:
            try:
                semantic_memories = await qdrant.search_memories(
                    query=query,
                    agent_id=agent_id,
                    limit=5,
                    min_score=0.4,  # Lower threshold to get more results
                )
                if semantic_memories:
                    # Format memories with importance indicator
                    formatted = []
                    for mem in semantic_memories:
                        importance = "⭐" if mem["importance"] > 0.7 else ""
                        formatted.append(f"{mem['key']}: {mem['value']} {importance}".strip())
                    logger.debug(f"Found {len(formatted)} semantic memories for agent {agent_id}")
                    return formatted
            except Exception as e:
                logger.warning(f"Semantic memory search failed, using fallback: {e}")
        
        # Fall back to PostgreSQL memories
        return await self.db.get_agent_memories(agent_id)
    
    async def _save_agent_response(self, request: ExecuteRequest, output: str):
        """Save agent response as a message in the conversation."""
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages (id, office_id, conversation_id, sender_type, sender_id, content, metadata, created_at)
                VALUES (gen_random_uuid(), $1, $2, 'agent', $3, $4, '{}', NOW())
                """,
                request.office_id,
                request.conversation_id,
                request.agent_id,
                output,
            )
    
    async def _notify_backend(self, request: ExecuteRequest, output: str):
        """Notify the backend about the completed task (for WebSocket broadcast)."""
        try:
            api_key = self.settings.internal_api_key
            logger.debug(f"Notifying backend with API key: {api_key[:10]}...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.settings.backend_url}/api/v1/internal/task-complete",
                    json={
                        "task_id": request.task_id,
                        "conversation_id": request.conversation_id,
                        "agent_id": request.agent_id,
                        "output": output,
                    },
                    headers={
                        "X-Internal-API-Key": api_key,
                    },
                    timeout=5.0,
                )
                if response.status_code != 200:
                    logger.warning(f"Backend notification failed: {response.status_code}")
        except Exception as e:
            # Log but don't fail - message is already saved
            logger.warning(f"Failed to notify backend: {e}")


    async def execute_tool_plan(
        self, 
        plan: ActionPlan, 
        user_id: str, 
        office_id: str
    ) -> ExecutionResult:
        """
        Execute a tool action plan.
        
        Args:
            plan: The action plan to execute
            user_id: The ID of the user requesting execution
            office_id: The office context
            
        Returns:
            ExecutionResult containing outputs and status
        """
        # Ensure initialization
        await self.initialize()
        
        # Mock permissions for MVP - in production this comes from DB/Auth
        permissions = PermissionScope(
            user_id=user_id,
            office_id=office_id,
            granted_scopes=["*"],  # Allow all for MVP testing
            oauth_tokens={},       # Tokens would be injected here
        )
        
        context = ExecutionContext(
            user_id=user_id,
            office_id=office_id,
            permissions=permissions
        )
        
        return await self.tool_orchestrator.execute_plan(plan, context)


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get the orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
