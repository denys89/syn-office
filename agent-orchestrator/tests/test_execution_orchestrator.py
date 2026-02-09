"""Tests for Execution Orchestrator."""

import pytest
from datetime import datetime, timedelta
from tool_execution import (
    ExecutionOrchestrator,
    ActionPlan,
    ActionStep,
    ExecutionContext,
    PermissionScope,
    ExecutionStatus,
    ToolVendor,
    FailureHandling,
)


@pytest.fixture
def orchestrator():
    """Create a fresh orchestrator for each test."""
    return ExecutionOrchestrator()


@pytest.fixture
def sample_context():
    """Create sample execution context."""
    return ExecutionContext(
        user_id="user123",
        office_id="office456",
        permissions=PermissionScope(
            user_id="user123",
            office_id="office456",
            granted_scopes=["google.sheets.read", "google.sheets.write"],
            oauth_tokens={"google": "valid_token_12345678901234567890"},
            token_expiry={"google": datetime.utcnow() + timedelta(hours=1)},
        ),
    )


@pytest.fixture
def simple_plan():
    """Create a simple action plan."""
    return ActionPlan(
        steps=[
            ActionStep(
                step_id="step1",
                tool="google_sheets_read",
                inputs={
                    "spreadsheet_id": "test_id",
                    "range": "Sheet1!A1:B10",
                },
            ),
        ],
    )


class TestExecutionOrchestrator:
    """Test cases for ExecutionOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_initialize(self, orchestrator):
        """Test orchestrator initialization."""
        await orchestrator.initialize()
        
        assert orchestrator.is_initialized
    
    @pytest.mark.asyncio
    async def test_execute_simple_plan(self, orchestrator, simple_plan, sample_context):
        """Test executing a simple single-step plan."""
        await orchestrator.initialize()
        
        result = await orchestrator.execute_plan(simple_plan, sample_context)
        
        assert result.execution_id == simple_plan.execution_id
        assert result.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILURE]
        assert len(result.step_results) == 1
    
    @pytest.mark.asyncio
    async def test_execute_multi_step_plan(self, orchestrator, sample_context):
        """Test executing a multi-step plan."""
        await orchestrator.initialize()
        
        plan = ActionPlan(
            steps=[
                ActionStep(
                    step_id="step1",
                    tool="google_sheets_create",
                    inputs={"title": "Test Sheet"},
                ),
                ActionStep(
                    step_id="step2",
                    tool="google_sheets_read",
                    inputs={
                        "spreadsheet_id": "result_from_step1",
                        "range": "Sheet1!A1:B10",
                    },
                    depends_on=["step1"],
                ),
            ],
        )
        
        result = await orchestrator.execute_plan(plan, sample_context)
        
        assert result.execution_id == plan.execution_id
        assert len(result.step_results) == 2
    
    @pytest.mark.asyncio
    async def test_execute_plan_permission_denied(self, orchestrator):
        """Test plan execution fails with insufficient permissions."""
        await orchestrator.initialize()
        
        # Context without required permissions
        context = ExecutionContext(
            user_id="user123",
            office_id="office456",
            permissions=PermissionScope(
                user_id="user123",
                office_id="office456",
                granted_scopes=[],  # No permissions
            ),
        )
        
        plan = ActionPlan(
            steps=[
                ActionStep(
                    step_id="step1",
                    tool="google_sheets_read",
                    inputs={
                        "spreadsheet_id": "test_id",
                        "range": "Sheet1!A1:B10",
                    },
                ),
            ],
        )
        
        result = await orchestrator.execute_plan(plan, context)
        
        assert result.status == ExecutionStatus.BLOCKED
        assert "Permission" in result.message or "permission" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_plan_invalid_tool(self, orchestrator, sample_context):
        """Test plan execution fails with invalid tool."""
        await orchestrator.initialize()
        
        plan = ActionPlan(
            steps=[
                ActionStep(
                    step_id="step1",
                    tool="nonexistent_tool",
                    inputs={},
                ),
            ],
        )
        
        result = await orchestrator.execute_plan(plan, sample_context)
        
        assert result.status == ExecutionStatus.FAILURE
        assert "Unknown tool" in result.message or len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_execute_internal_tool(self, orchestrator):
        """Test executing internal tools (no OAuth needed)."""
        await orchestrator.initialize()
        
        context = ExecutionContext(
            user_id="user123",
            office_id="office456",
            permissions=PermissionScope(
                user_id="user123",
                office_id="office456",
                granted_scopes=[],
            ),
        )
        
        plan = ActionPlan(
            steps=[
                ActionStep(
                    step_id="step1",
                    tool="text_processing",
                    inputs={
                        "text": "Hello world. This is a test. Another sentence.",
                        "operation": "count",
                    },
                ),
            ],
        )
        
        result = await orchestrator.execute_plan(plan, context)
        
        # Internal tools should work without OAuth
        assert result.execution_id == plan.execution_id
        assert len(result.step_results) == 1
    
    @pytest.mark.asyncio
    async def test_step_failure_handling_stop(self, orchestrator, sample_context):
        """Test that STOP failure handling stops execution."""
        await orchestrator.initialize()
        
        plan = ActionPlan(
            steps=[
                ActionStep(
                    step_id="step1",
                    tool="nonexistent_tool",
                    inputs={},
                    failure_handling=FailureHandling.STOP,
                ),
                ActionStep(
                    step_id="step2",
                    tool="text_processing",
                    inputs={"text": "test", "operation": "count"},
                ),
            ],
        )
        
        result = await orchestrator.execute_plan(plan, sample_context)
        
        # With invalid tool in validation, execution should fail early
        assert result.status == ExecutionStatus.FAILURE
    
    @pytest.mark.asyncio
    async def test_get_active_executions(self, orchestrator):
        """Test getting list of active executions."""
        await orchestrator.initialize()
        
        active = orchestrator.get_active_executions()
        
        assert isinstance(active, list)
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, orchestrator):
        """Test parallel execution of independent steps."""
        await orchestrator.initialize()
        
        context = ExecutionContext(
            user_id="user123",
            office_id="office456",
            permissions=PermissionScope(
                user_id="user123",
                office_id="office456",
                granted_scopes=[],
            ),
        )
        
        plan = ActionPlan(
            steps=[
                ActionStep(
                    step_id="step1",
                    tool="text_processing",
                    inputs={"text": "Hello world", "operation": "count"},
                ),
                ActionStep(
                    step_id="step2",
                    tool="text_processing",
                    inputs={"text": "Another text here", "operation": "count"},
                ),
            ],
            parallel_execution=True,
        )
        
        result = await orchestrator.execute_plan(plan, context)
        
        assert len(result.step_results) == 2
