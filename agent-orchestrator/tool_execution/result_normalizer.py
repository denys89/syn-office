"""Result Normalizer - Unified response formatting.

Converts heterogeneous tool responses into a unified format
for downstream consumption.
"""

import logging
from typing import List, Optional
from datetime import datetime

from .types import (
    AdapterResult,
    StepResult,
    ExecutionResult,
    ExecutionStatus,
    Artifact,
)

logger = logging.getLogger(__name__)


class ResultNormalizer:
    """
    Normalize heterogeneous responses to unified format.
    
    Consumers:
    - Result Validation Layer
    - User Interface Layer
    - Audit & Logging Systems
    
    Output Format:
    - status: success | partial_success | failure
    - execution_id: uuid
    - artifacts: list of output artifacts
    - message: human-readable summary
    - errors: list of error messages
    """
    
    def __init__(self):
        self._initialized: bool = False
    
    async def initialize(self) -> None:
        """Initialize the normalizer."""
        self._initialized = True
        logger.info("Result Normalizer initialized")
    
    def normalize_step(
        self,
        step_id: str,
        tool: str,
        adapter_result: AdapterResult,
        retry_count: int = 0,
    ) -> StepResult:
        """
        Convert adapter result to normalized step result.
        
        Args:
            step_id: ID of the step
            tool: Tool name that was executed
            adapter_result: Raw result from adapter
            retry_count: Number of retries attempted
            
        Returns:
            Normalized StepResult
        """
        if adapter_result.success:
            status = ExecutionStatus.SUCCESS
        else:
            status = ExecutionStatus.FAILURE
        
        return StepResult(
            step_id=step_id,
            tool=tool,
            status=status,
            artifacts=adapter_result.artifacts,
            output=adapter_result.data,
            error=adapter_result.error,
            latency_ms=adapter_result.latency_ms,
            retry_count=retry_count,
        )
    
    def normalize_execution(
        self,
        execution_id: str,
        step_results: List[StepResult],
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> ExecutionResult:
        """
        Convert step results to normalized execution result.
        
        Args:
            execution_id: ID of the execution
            step_results: Results from each step
            started_at: When execution started
            completed_at: When execution completed
            
        Returns:
            Normalized ExecutionResult
        """
        # Count successes and failures
        steps_completed = sum(
            1 for r in step_results if r.status == ExecutionStatus.SUCCESS
        )
        steps_failed = sum(
            1 for r in step_results if r.status == ExecutionStatus.FAILURE
        )
        
        # Determine overall status
        if steps_failed == 0:
            status = ExecutionStatus.SUCCESS
        elif steps_completed == 0:
            status = ExecutionStatus.FAILURE
        else:
            status = ExecutionStatus.PARTIAL_SUCCESS
        
        # Collect all artifacts
        all_artifacts: List[Artifact] = []
        for result in step_results:
            all_artifacts.extend(result.artifacts)
        
        # Collect all errors
        errors = [r.error for r in step_results if r.error]
        
        # Calculate total latency
        total_latency = sum(r.latency_ms for r in step_results)
        
        # Generate message
        message = self._generate_message(status, len(step_results), steps_completed, steps_failed)
        
        return ExecutionResult(
            status=status,
            execution_id=execution_id,
            artifacts=all_artifacts,
            message=message,
            errors=errors,
            step_results=step_results,
            total_latency_ms=total_latency,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            started_at=started_at,
            completed_at=completed_at,
        )
    
    def _generate_message(
        self,
        status: ExecutionStatus,
        total_steps: int,
        completed: int,
        failed: int,
    ) -> str:
        """Generate human-readable summary message."""
        if status == ExecutionStatus.SUCCESS:
            if total_steps == 1:
                return "Task completed successfully."
            return f"All {total_steps} steps completed successfully."
        
        elif status == ExecutionStatus.PARTIAL_SUCCESS:
            return f"Partial success: {completed}/{total_steps} steps completed, {failed} failed."
        
        elif status == ExecutionStatus.FAILURE:
            if total_steps == 1:
                return "Task failed."
            return f"Execution failed: {failed}/{total_steps} steps failed."
        
        else:
            return f"Execution {status.value}: {completed}/{total_steps} steps completed."
    
    def create_error_result(
        self,
        execution_id: str,
        error: str,
        error_code: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Create a failure result for early errors.
        
        Args:
            execution_id: ID of the execution
            error: Error message
            error_code: Optional error code
            
        Returns:
            ExecutionResult with failure status
        """
        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            execution_id=execution_id,
            artifacts=[],
            message=f"Execution failed: {error}",
            errors=[error],
            step_results=[],
            total_latency_ms=0,
            steps_completed=0,
            steps_failed=0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
    
    def create_blocked_result(
        self,
        execution_id: str,
        reason: str,
    ) -> ExecutionResult:
        """
        Create a blocked result for permission/quota issues.
        
        Args:
            execution_id: ID of the execution
            reason: Why execution was blocked
            
        Returns:
            ExecutionResult with blocked status
        """
        return ExecutionResult(
            status=ExecutionStatus.BLOCKED,
            execution_id=execution_id,
            artifacts=[],
            message=f"Execution blocked: {reason}",
            errors=[reason],
            step_results=[],
            total_latency_ms=0,
            steps_completed=0,
            steps_failed=0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
    
    def merge_results(
        self,
        results: List[ExecutionResult],
    ) -> ExecutionResult:
        """
        Merge multiple execution results into one.
        
        Useful for parallel execution batches.
        
        Args:
            results: List of execution results to merge
            
        Returns:
            Combined ExecutionResult
        """
        if not results:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                execution_id="merged",
                artifacts=[],
                message="No results to merge.",
                errors=[],
                step_results=[],
            )
        
        all_artifacts = []
        all_errors = []
        all_steps = []
        total_latency = 0
        total_completed = 0
        total_failed = 0
        
        earliest_start = None
        latest_end = None
        
        for result in results:
            all_artifacts.extend(result.artifacts)
            all_errors.extend(result.errors)
            all_steps.extend(result.step_results)
            total_latency += result.total_latency_ms
            total_completed += result.steps_completed
            total_failed += result.steps_failed
            
            if result.started_at:
                if earliest_start is None or result.started_at < earliest_start:
                    earliest_start = result.started_at
            
            if result.completed_at:
                if latest_end is None or result.completed_at > latest_end:
                    latest_end = result.completed_at
        
        # Determine overall status
        if total_failed == 0:
            status = ExecutionStatus.SUCCESS
        elif total_completed == 0:
            status = ExecutionStatus.FAILURE
        else:
            status = ExecutionStatus.PARTIAL_SUCCESS
        
        total_steps = total_completed + total_failed
        message = self._generate_message(status, total_steps, total_completed, total_failed)
        
        return ExecutionResult(
            status=status,
            execution_id="merged",
            artifacts=all_artifacts,
            message=message,
            errors=all_errors,
            step_results=all_steps,
            total_latency_ms=total_latency,
            steps_completed=total_completed,
            steps_failed=total_failed,
            started_at=earliest_start,
            completed_at=latest_end,
        )


# Singleton instance
_normalizer: Optional[ResultNormalizer] = None


async def get_result_normalizer() -> ResultNormalizer:
    """Get or create the result normalizer singleton."""
    global _normalizer
    if _normalizer is None:
        _normalizer = ResultNormalizer()
        await _normalizer.initialize()
    return _normalizer
