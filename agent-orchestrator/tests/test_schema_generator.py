import pytest
from tool_execution import ToolDefinition, ToolSchemaGenerator, ToolCategory, ToolVendor, ToolInputSchema

def test_generate_schema_basic():
    tool = ToolDefinition(
        tool_name="test_tool",
        description="A test tool",
        category=ToolCategory.SYSTEM,
        vendor=ToolVendor.INTERNAL,
        input_schema=ToolInputSchema(
            type="object",
            properties={"arg1": {"type": "string"}}
        )
    )
    
    schema = ToolSchemaGenerator.generate_schema(tool)
    
    assert schema["name"] == "test_tool"
    assert schema["description"] == "A test tool"
    assert schema["parameters"]["properties"]["arg1"]["type"] == "string"

def test_generate_schemas_list():
    tools = [
        ToolDefinition(name="t1", tool_name="t1", description="d1", category=ToolCategory.SYSTEM, vendor=ToolVendor.INTERNAL),
        ToolDefinition(name="t2", tool_name="t2", description="d2", category=ToolCategory.SYSTEM, vendor=ToolVendor.INTERNAL)
    ]
    
    schemas = ToolSchemaGenerator.generate_schemas(tools)
    
    assert len(schemas) == 2
    assert schemas[0]["name"] == "t1"
    assert schemas[1]["name"] == "t2"

def test_generate_prompt_text():
    tools = [
        ToolDefinition(name="t1", tool_name="t1", description="d1", category=ToolCategory.SYSTEM, vendor=ToolVendor.INTERNAL)
    ]
    
    text = ToolSchemaGenerator.generate_prompt_text(tools)
    assert "t1" in text
    assert "d1" in text
    assert "[" in text  # JSON list
