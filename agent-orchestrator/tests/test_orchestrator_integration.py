"""Integration tests for Orchestrator -> Tool Execution integration."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from orchestrator import Orchestrator, get_orchestrator
from tool_execution import ActionPlan, ActionStep, ExecutionResult, ExecutionStatus

@pytest.fixture
def mock_orchestrator():
    with patch('orchestrator.get_database'), \
         patch('orchestrator.get_settings'), \
         patch('orchestrator.get_model_selector'), \
         patch('orchestrator.get_metrics_service'), \
         patch('orchestrator.get_credit_client'), \
         patch('orchestrator.get_cost_engine'), \
         patch('orchestrator.get_rate_limiter'), \
         patch('orchestrator.get_anomaly_detector'), \
         patch('orchestrator.get_circuit_breaker'), \
         patch('orchestrator.get_anomaly_detector'), \
         patch('orchestrator.get_circuit_breaker'), \
         patch('orchestrator.get_execution_orchestrator', new_callable=AsyncMock) as mock_get_tool_orch:
        
        # Setup mock tool orchestrator instance (returned by the async factory)
        mock_tool_orch_instance = MagicMock()
        # Add async execute_plan method
        mock_tool_orch_instance.execute_plan = AsyncMock()
        mock_tool_orch_instance.initialize = AsyncMock()
        
        mock_get_tool_orch.return_value = mock_tool_orch_instance
        
        orch = Orchestrator()
        # We don't set tool_orchestrator here because check_tool_plan calls initialize() 
        # which calls get_execution_orchestrator() which returns our mock
        return orch

@pytest.mark.asyncio
async def test_execute_tool_plan_delegation(mock_orchestrator):
    """Test that execute_tool_plan correctly delegates to tool_orchestrator."""
    # Arrange
    plan = ActionPlan(steps=[])
    user_id = "test_user"
    office_id = "test_office"
    
    expected_result = ExecutionResult(
        execution_id="test_exec",
        status=ExecutionStatus.SUCCESS,
        artifacts=[],
        message="Success",
        errors=[],
        step_results=[]
    )
    
    # Configure mock
    # Access the mock instance that will be returned
    mock_tool_instance = mock_orchestrator.tool_orchestrator = mock_orchestrator.tool_orchestrator or AsyncMock()
    # Actually, verify against the mock returned by the patched function
    # But since we call initialize(), self.tool_orchestrator gets set.
    
    # Let's rely on the patch return value
    # We need to access the mock we set up in the fixture
    # But fixture returns 'orch', not the mocks. 
    # Let's just set the instance on the orchestrator directly for the test 
    # OR rely on initialize() setting it.
    
    # In test_execute_tool_plan_delegation, we call execute_tool_plan -> initialize -> get_execution_orchestrator
    
    # We need to get the specific mock instance to configure response
    # Since we can't easily access the fixture's local variables, 
    # let's re-patch or structure the test differently. 
    pass # Replaced by full rewrite below

@pytest.mark.asyncio
async def test_execute_tool_plan_delegation():
    """Test that execute_tool_plan correctly delegates to tool_orchestrator."""
    # Custom patch setup
    with patch('orchestrator.get_database'), \
         patch('orchestrator.get_settings'), \
         patch('orchestrator.get_model_selector'), \
         patch('orchestrator.get_metrics_service'), \
         patch('orchestrator.get_credit_client'), \
         patch('orchestrator.get_cost_engine'), \
         patch('orchestrator.get_rate_limiter'), \
         patch('orchestrator.get_anomaly_detector'), \
         patch('orchestrator.get_circuit_breaker'), \
         patch('orchestrator.get_execution_orchestrator', new_callable=AsyncMock) as mock_get_tool_orch:
            
        mock_tool_instance = MagicMock()
        mock_tool_instance.execute_plan = AsyncMock()
        mock_tool_instance.initialize = AsyncMock()
        mock_get_tool_orch.return_value = mock_tool_instance

        orch = Orchestrator()
        
        # Arrange
        plan = ActionPlan(steps=[])
        user_id = "test_user"
        office_id = "test_office"
        
        expected_result = ExecutionResult(
            execution_id="test_exec",
            status=ExecutionStatus.SUCCESS,
            artifacts=[],
            message="Success",
            errors=[],
            step_results=[]
        )
        
        mock_tool_instance.execute_plan.return_value = expected_result
        
        # Act
        result = await orch.execute_tool_plan(plan, user_id, office_id)
        
        # Assert
        assert result == expected_result
        # initialize calls get_execution_orchestrator
        mock_get_tool_orch.assert_awaited_once()
        # tool_orchestrator.execute_plan is called
        mock_tool_instance.execute_plan.assert_awaited_once()
        
        call_args = mock_tool_instance.execute_plan.call_args
        assert call_args is not None
        context = call_args[0][1]
        assert context.user_id == user_id
        assert context.office_id == office_id
