"""Tests for Tool Registry."""

import pytest
from tool_execution import (
    ToolRegistry,
    ToolDefinition,
    ToolCategory,
    ToolVendor,
    CostLevel,
    RetryPolicy,
)


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return ToolRegistry()


@pytest.fixture
async def initialized_registry():
    """Create an initialized registry with default tools."""
    registry = ToolRegistry()
    await registry.initialize()
    return registry


class TestToolRegistry:
    """Test cases for ToolRegistry."""
    
    def test_register_tool(self, registry):
        """Test registering a new tool."""
        tool = ToolDefinition(
            tool_name="test_tool",
            description="A test tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
        )
        
        registry.register_tool(tool)
        
        assert registry.validate_tool_exists("test_tool")
        assert registry.tool_count == 1
    
    def test_register_duplicate_tool_raises(self, registry):
        """Test that registering duplicate tool raises error."""
        tool = ToolDefinition(
            tool_name="test_tool",
            description="A test tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
        )
        
        registry.register_tool(tool)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register_tool(tool)
    
    def test_get_tool(self, registry):
        """Test getting a tool by name."""
        tool = ToolDefinition(
            tool_name="test_tool",
            description="A test tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
        )
        
        registry.register_tool(tool)
        
        retrieved = registry.get_tool("test_tool")
        assert retrieved is not None
        assert retrieved.tool_name == "test_tool"
    
    def test_get_nonexistent_tool_returns_none(self, registry):
        """Test getting non-existent tool returns None."""
        result = registry.get_tool("nonexistent")
        assert result is None
    
    def test_list_tools_by_category(self, registry):
        """Test listing tools filtered by category."""
        tool1 = ToolDefinition(
            tool_name="data_tool",
            description="Data tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
        )
        tool2 = ToolDefinition(
            tool_name="doc_tool",
            description="Document tool",
            category=ToolCategory.DOCUMENT,
            vendor=ToolVendor.INTERNAL,
        )
        
        registry.register_tool(tool1)
        registry.register_tool(tool2)
        
        data_tools = registry.list_tools(category=ToolCategory.DATA)
        assert len(data_tools) == 1
        assert data_tools[0].tool_name == "data_tool"
    
    def test_list_tools_by_vendor(self, registry):
        """Test listing tools filtered by vendor."""
        tool1 = ToolDefinition(
            tool_name="google_tool",
            description="Google tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.GOOGLE,
        )
        tool2 = ToolDefinition(
            tool_name="internal_tool",
            description="Internal tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
        )
        
        registry.register_tool(tool1)
        registry.register_tool(tool2)
        
        google_tools = registry.list_tools(vendor=ToolVendor.GOOGLE)
        assert len(google_tools) == 1
        assert google_tools[0].tool_name == "google_tool"
    
    def test_get_required_permissions(self, registry):
        """Test getting required permissions for a tool."""
        tool = ToolDefinition(
            tool_name="test_tool",
            description="A test tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.sheets.read", "google.sheets.write"],
        )
        
        registry.register_tool(tool)
        
        permissions = registry.get_required_permissions("test_tool")
        assert "google.sheets.read" in permissions
        assert "google.sheets.write" in permissions
    
    def test_validate_inputs_success(self, registry):
        """Test input validation with valid inputs."""
        tool = ToolDefinition(
            tool_name="test_tool",
            description="A test tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )
        
        registry.register_tool(tool)
        
        valid, error = registry.validate_inputs("test_tool", {"name": "test"})
        assert valid
        assert error is None
    
    def test_validate_inputs_missing_required(self, registry):
        """Test input validation with missing required field."""
        tool = ToolDefinition(
            tool_name="test_tool",
            description="A test tool",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )
        
        registry.register_tool(tool)
        
        valid, error = registry.validate_inputs("test_tool", {})
        assert not valid
        assert "name" in error
    
    @pytest.mark.asyncio
    async def test_initialize_registers_default_tools(self, initialized_registry):
        """Test that initialize registers default tools."""
        registry = initialized_registry
        
        assert registry.is_initialized
        assert registry.tool_count > 0
        
        # Check some expected default tools
        assert registry.validate_tool_exists("google_sheets_create")
        assert registry.validate_tool_exists("google_sheets_read")
        assert registry.validate_tool_exists("data_transform")
