import pytest
from tool_execution import ActionPlanParser, ActionPlan

def test_extract_json_block_markdown():
    text = """
    Here is the plan:
    ```json
    {
        "execution_id": "exec-1",
        "description": "Test plan",
        "steps": []
    }
    ```
    """
    json_str = ActionPlanParser.extract_json_block(text)
    assert json_str is not None
    assert '"execution_id": "exec-1"' in json_str

def test_extract_json_block_raw():
    text = '{ "execution_id": "exec-1", "steps": [] }'
    json_str = ActionPlanParser.extract_json_block(text)
    assert json_str == text

def test_parse_valid_plan():
    text = """
    ```json
    {
        "execution_id": "exec-1",
        "description": "Test plan",
        "steps": [
            {
                "step_id": "s1",
                "tool": "test_tool",
                "inputs": {}
            }
        ]
    }
    ```
    """
    plan = ActionPlanParser.parse(text)
    assert isinstance(plan, ActionPlan)
    assert plan.execution_id == "exec-1"
    assert len(plan.steps) == 1

def test_parse_invalid_json():
    text = "```json { invalid } ```"
    plan = ActionPlanParser.parse(text)
    assert plan is None

def test_parse_no_json():
    text = "Just some text"
    plan = ActionPlanParser.parse(text)
    assert plan is None
