"""Execution Orchestrator - Coordinates tool execution for action plans.

The main entry point for the Tool Execution Layer that coordinates
all components to execute action plans deterministically.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Dict, List, Any

from .types import (
    ActionPlan,
    ActionStep,
    ExecutionResult,
    ExecutionContext,
    ExecutionStatus,
    StepResult,
    FailureHandling,
    ToolVendor,
    PermissionScope,
)
from .tool_registry import ToolRegistry, get_tool_registry
from .security_gateway import SecurityGateway, get_security_gateway
from .quota_manager import QuotaManager, get_quota_manager
from .result_normalizer import ResultNormalizer, get_result_normalizer
from .adapters.base import BaseToolAdapter
from .adapters.google_workspace import GoogleWorkspaceAdapter
from .adapters.internal import InternalToolAdapter

logger = logging.getLogger(__name__)


class ExecutionOrchestrator:
    """
    Coordinates execution of one or more tools in a controlled sequence.
    
    Responsibilities:
    - Execute step-by-step action plans
    - Track execution state
    - Handle retries and fallbacks
    - Support partial success handling
    
    Principles:
    - Deterministic execution
    - Strong observability
    - Secure-by-default
    - Vendor-agnostic abstraction
    
    This layer does NOT:
    - Interpret user intent
    - Make business decisions
    - Modify user goals
    - Store long-term memory
    """
    
    def __init__(self):
        self._initialized: bool = False
        self._registry: Optional[ToolRegistry] = None
        self._security: Optional[SecurityGateway] = None
        self._quotas: Optional[QuotaManager] = None
        self._normalizer: Optional[ResultNormalizer] = None
        
        # Adapters by vendor
        self._adapters: Dict[ToolVendor, BaseToolAdapter] = {}
        
        # Execution state
        self._active_executions: Dict[str, ActionPlan] = {}
    
    async def initialize(self) -> None:
        """Initialize the orchestrator and all dependencies."""
        logger.info("Initializing Execution Orchestrator...")
        
        # Initialize dependencies
        self._registry = await get_tool_registry()
        self._security = await get_security_gateway()
        self._quotas = await get_quota_manager()
        self._normalizer = await get_result_normalizer()
        
        # Initialize adapters
        google_adapter = GoogleWorkspaceAdapter()
        await google_adapter.initialize()
        self._adapters[ToolVendor.GOOGLE] = google_adapter
        
        internal_adapter = InternalToolAdapter()
        await internal_adapter.initialize()
        self._adapters[ToolVendor.INTERNAL] = internal_adapter
        
        self._initialized = True
        logger.info("Execution Orchestrator initialized successfully")
    
    async def execute_plan(
        self,
        plan: ActionPlan,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Execute all steps in an action plan.
        
        Execution flow:
        1. Validate plan against registry
        2. Check permissions for all tools
        3. Verify quotas
        4. Execute steps (sequential/parallel)
        5. Handle failures and retries
        6. Normalize and return results
        
        Args:
            plan: Action plan to execute
            context: Execution context with user info and permissions
            
        Returns:
            ExecutionResult with all step results and artifacts
        """
        if not self._initialized:
            await self.initialize()
        
        execution_id = plan.execution_id
        started_at = datetime.utcnow()
        
        logger.info(f"Starting execution {execution_id} with {len(plan.steps)} steps")
        
        # Track active execution
        self._active_executions[execution_id] = plan
        
        try:
            # 1. Validate plan
            validation_result = await self._validate_plan(plan)
            if not validation_result['valid']:
                return self._normalizer.create_error_result(
                    execution_id,
                    validation_result['error'],
                )
            
            # 2. Check permissions for all tools
            permission_result = await self._check_all_permissions(plan, context)
            if not permission_result['allowed']:
                return self._normalizer.create_blocked_result(
                    execution_id,
                    permission_result['reason'],
                )
            
            # 3. Check quotas
            quota_result = await self._check_all_quotas(plan, context)
            if not quota_result['allowed']:
                return self._normalizer.create_blocked_result(
                    execution_id,
                    quota_result['reason'],
                )
            
            # 4. Execute steps
            if plan.parallel_execution:
                step_results = await self._execute_parallel(plan, context)
            else:
                step_results = await self._execute_sequential(plan, context)
            
            # 5. Normalize results
            completed_at = datetime.utcnow()
            result = self._normalizer.normalize_execution(
                execution_id,
                step_results,
                started_at,
                completed_at,
            )
            
            logger.info(
                f"Execution {execution_id} completed: "
                f"{result.steps_completed} succeeded, {result.steps_failed} failed"
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Execution {execution_id} failed: {e}")
            return self._normalizer.create_error_result(
                execution_id,
                str(e),
            )
        finally:
            # Cleanup
            self._active_executions.pop(execution_id, None)
    
    async def execute_step(
        self,
        step: ActionStep,
        context: ExecutionContext,
    ) -> StepResult:
        """
        Execute a single step.
        
        Args:
            step: Step to execute
            context: Execution context
            
        Returns:
            StepResult with outcome
        """
        tool_name = step.tool
        step_id = step.step_id
        
        logger.info(f"Executing step {step_id}: {tool_name}")
        step.status = ExecutionStatus.RUNNING
        step.started_at = datetime.utcnow()
        
        # Get tool definition
        tool = self._registry.get_tool(tool_name)
        if not tool:
            step.status = ExecutionStatus.FAILURE
            step.error = f"Tool not found: {tool_name}"
            step.completed_at = datetime.utcnow()
            return self._normalizer.normalize_step(
                step_id, tool_name,
                self._create_error_adapter_result(step.error),
            )
        
        # Get adapter
        adapter = self._adapters.get(tool.vendor)
        if not adapter:
            step.status = ExecutionStatus.FAILURE
            step.error = f"No adapter for vendor: {tool.vendor}"
            step.completed_at = datetime.utcnow()
            return self._normalizer.normalize_step(
                step_id, tool_name,
                self._create_error_adapter_result(step.error),
            )
        
        # Track quota
        self._quotas.increment_active(context.user_id, tool.vendor)
        
        try:
            # Execute with retry logic
            result = await self._execute_with_retry(
                adapter, step, context, tool
            )
            
            # Record usage
            self._quotas.record_usage(tool_name, tool.vendor, context.user_id)
            
            step.status = ExecutionStatus.SUCCESS if result.success else ExecutionStatus.FAILURE
            step.result = result.data
            step.error = result.error
            step.completed_at = datetime.utcnow()
            
            return self._normalizer.normalize_step(
                step_id, tool_name, result
            )
            
        finally:
            self._quotas.decrement_active(context.user_id, tool.vendor)
    
    async def _execute_sequential(
        self,
        plan: ActionPlan,
        context: ExecutionContext,
    ) -> List[StepResult]:
        """Execute steps sequentially."""
        results: List[StepResult] = []
        shared_data = dict(context.shared_data)
        
        for step in plan.steps:
            # Update context with accumulated shared data
            updated_context = ExecutionContext(
                user_id=context.user_id,
                office_id=context.office_id,
                permissions=context.permissions,
                shared_data=shared_data,
                dry_run=context.dry_run,
            )
            
            # Check dependencies
            if step.depends_on:
                deps_met = all(
                    self._is_step_successful(results, dep_id)
                    for dep_id in step.depends_on
                )
                if not deps_met:
                    result = self._normalizer.normalize_step(
                        step.step_id,
                        step.tool,
                        self._create_error_adapter_result("Dependencies not met"),
                    )
                    results.append(result)
                    continue
            
            # Execute step
            result = await self.execute_step(step, updated_context)
            results.append(result)
            
            # Update shared data with step output
            if result.output:
                shared_data[step.step_id] = result.output
            
            # Handle failure
            if result.status == ExecutionStatus.FAILURE:
                if step.failure_handling == FailureHandling.STOP:
                    logger.warning(f"Stopping execution due to step failure: {step.step_id}")
                    break
                elif step.failure_handling == FailureHandling.CONTINUE:
                    continue
        
        return results
    
    async def _execute_parallel(
        self,
        plan: ActionPlan,
        context: ExecutionContext,
    ) -> List[StepResult]:
        """Execute independent steps in parallel."""
        # Group steps by dependencies
        independent_steps = [s for s in plan.steps if not s.depends_on]
        dependent_steps = [s for s in plan.steps if s.depends_on]
        
        results: List[StepResult] = []
        completed_step_ids = set()
        
        # Execute independent steps in parallel
        if independent_steps:
            tasks = [
                self.execute_step(step, context)
                for step in independent_steps
            ]
            independent_results = await asyncio.gather(*tasks)
            results.extend(independent_results)
            
            for step, result in zip(independent_steps, independent_results):
                if result.status == ExecutionStatus.SUCCESS:
                    completed_step_ids.add(step.step_id)
        
        # Execute dependent steps sequentially
        for step in dependent_steps:
            deps_met = all(dep_id in completed_step_ids for dep_id in step.depends_on)
            if not deps_met:
                result = self._normalizer.normalize_step(
                    step.step_id,
                    step.tool,
                    self._create_error_adapter_result("Dependencies not met"),
                )
                results.append(result)
                continue
            
            result = await self.execute_step(step, context)
            results.append(result)
            
            if result.status == ExecutionStatus.SUCCESS:
                completed_step_ids.add(step.step_id)
        
        return results
    
    async def _execute_with_retry(
        self,
        adapter: BaseToolAdapter,
        step: ActionStep,
        context: ExecutionContext,
        tool: Any,
    ):
        """Execute step with retry logic based on tool's retry policy."""
        from .types import AdapterResult, RetryPolicy
        
        max_retries = tool.max_retries
        retry_policy = tool.retry_policy
        
        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                # Calculate delay
                if retry_policy == RetryPolicy.FIXED:
                    delay = 1.0
                elif retry_policy == RetryPolicy.EXPONENTIAL:
                    delay = 2 ** (attempt - 1)
                else:
                    delay = 0
                
                logger.info(f"Retrying step {step.step_id}, attempt {attempt + 1}, delay {delay}s")
                await asyncio.sleep(delay)
            
            try:
                result = await adapter.execute(step, context)
                
                if result.success:
                    return result
                
                last_error = result.error
                
                # Don't retry on certain error codes
                if result.error_code in ('PERMISSION_DENIED', 'NOT_FOUND', 'INVALID_INPUT'):
                    return result
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {e}")
        
        return AdapterResult(
            success=False,
            error=f"All {max_retries + 1} attempts failed. Last error: {last_error}",
            error_code="RETRY_EXHAUSTED",
        )
    
    async def _validate_plan(self, plan: ActionPlan) -> Dict[str, Any]:
        """Validate plan against tool registry."""
        for step in plan.steps:
            if not self._registry.validate_tool_exists(step.tool):
                return {
                    'valid': False,
                    'error': f"Unknown tool: {step.tool}",
                }
            
            # Validate inputs
            valid, error = self._registry.validate_inputs(step.tool, step.inputs)
            if not valid:
                return {
                    'valid': False,
                    'error': f"Invalid inputs for {step.tool}: {error}",
                }
        
        return {'valid': True}
    
    async def _check_all_permissions(
        self,
        plan: ActionPlan,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Check permissions for all tools in plan."""
        for step in plan.steps:
            tool = self._registry.get_tool(step.tool)
            if tool:
                result = self._security.check_permissions(tool, context.permissions)
                if not result.allowed:
                    return {
                        'allowed': False,
                        'reason': f"Permission denied for {step.tool}: {result.reason}",
                    }
        
        return {'allowed': True}
    
    async def _check_all_quotas(
        self,
        plan: ActionPlan,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Check quotas for all tools in plan."""
        for step in plan.steps:
            tool = self._registry.get_tool(step.tool)
            if tool:
                result = self._quotas.check_quota(
                    step.tool, tool.vendor, context.user_id
                )
                if not result.allowed:
                    return {
                        'allowed': False,
                        'reason': f"Quota exceeded for {tool.vendor.value}: {result.reason}",
                    }
        
        return {'allowed': True}
    
    def _is_step_successful(self, results: List[StepResult], step_id: str) -> bool:
        """Check if a step completed successfully."""
        for result in results:
            if result.step_id == step_id:
                return result.status == ExecutionStatus.SUCCESS
        return False
    
    def _create_error_adapter_result(self, error: str):
        """Create an error AdapterResult."""
        from .types import AdapterResult
        return AdapterResult(
            success=False,
            error=error,
            error_code="ORCHESTRATOR_ERROR",
        )
    
    async def resume_plan(self, execution_id: str) -> ExecutionResult:
        """
        Resume a partially completed plan.
        
        Args:
            execution_id: ID of execution to resume
            
        Returns:
            ExecutionResult from resumed execution
        """
        if execution_id not in self._active_executions:
            return self._normalizer.create_error_result(
                execution_id,
                f"No active execution found with ID: {execution_id}",
            )
        
        plan = self._active_executions[execution_id]
        
        # Find incomplete steps
        incomplete_steps = [
            step for step in plan.steps
            if step.status in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING)
        ]
        
        if not incomplete_steps:
            return self._normalizer.create_error_result(
                execution_id,
                "No incomplete steps to resume",
            )
        
        # Create new plan with only incomplete steps
        resume_plan = ActionPlan(
            execution_id=execution_id,
            steps=incomplete_steps,
            context=plan.context,
            parallel_execution=plan.parallel_execution,
        )
        
        # Need context to resume - would need to be stored
        # For now, return error
        return self._normalizer.create_error_result(
            execution_id,
            "Resume not fully implemented - context not available",
        )
    
    def get_active_executions(self) -> List[str]:
        """Get list of active execution IDs."""
        return list(self._active_executions.keys())
    
    @property
    def is_initialized(self) -> bool:
        """Check if orchestrator is initialized."""
        return self._initialized


# Singleton instance
_orchestrator: Optional[ExecutionOrchestrator] = None


async def get_execution_orchestrator() -> ExecutionOrchestrator:
    """Get or create the execution orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ExecutionOrchestrator()
        await _orchestrator.initialize()
    return _orchestrator
