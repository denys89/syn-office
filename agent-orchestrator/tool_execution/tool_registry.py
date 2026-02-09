"""Tool Registry - Central catalog of executable tools.

The Tool Registry is the source of truth for all available tools.
Planning Layer selects tools exclusively from this registry.
Tools not in registry cannot be executed.
"""

import logging
from typing import Optional, Dict, List
from .types import ToolDefinition, ToolCategory, ToolVendor

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central catalog of all executable tools available to the AI Agent.
    
    Responsibilities:
    - Define tool metadata
    - Declare required permissions
    - Define input/output schemas
    - Provide execution constraints
    
    Design Notes:
    - Machine-readable format
    - Strict schema validation
    - Tools not registered cannot be executed
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._initialized: bool = False
    
    async def initialize(self) -> None:
        """Initialize registry with default tools."""
        self._register_default_tools()
        self._initialized = True
        logger.info(f"Tool Registry initialized with {len(self._tools)} tools")
    
    def register_tool(self, tool: ToolDefinition) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool definition to register
            
        Raises:
            ValueError: If tool with same name already exists
        """
        if tool.tool_name in self._tools:
            raise ValueError(f"Tool '{tool.tool_name}' is already registered")
        
        self._tools[tool.tool_name] = tool
        logger.info(f"Registered tool: {tool.tool_name} (vendor: {tool.vendor})")
    
    def update_tool(self, tool: ToolDefinition) -> None:
        """
        Update an existing tool definition.
        
        Args:
            tool: Updated tool definition
            
        Raises:
            KeyError: If tool doesn't exist
        """
        if tool.tool_name not in self._tools:
            raise KeyError(f"Tool '{tool.tool_name}' not found in registry")
        
        self._tools[tool.tool_name] = tool
        logger.info(f"Updated tool: {tool.tool_name}")
    
    def unregister_tool(self, tool_name: str) -> None:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: Name of tool to remove
            
        Raises:
            KeyError: If tool doesn't exist
        """
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found in registry")
        
        del self._tools[tool_name]
        logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool definition or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        vendor: Optional[ToolVendor] = None,
        available_only: bool = True
    ) -> List[ToolDefinition]:
        """
        List tools with optional filtering.
        
        Args:
            category: Filter by category
            vendor: Filter by vendor
            available_only: Only return available tools
            
        Returns:
            List of matching tool definitions
        """
        tools = list(self._tools.values())
        
        if available_only:
            tools = [t for t in tools if t.available]
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        if vendor:
            tools = [t for t in tools if t.vendor == vendor]
        
        return tools
    
    def validate_tool_exists(self, tool_name: str) -> bool:
        """
        Check if a tool exists in the registry.
        
        Args:
            tool_name: Name to check
            
        Returns:
            True if tool exists
        """
        return tool_name in self._tools
    
    def get_required_permissions(self, tool_name: str) -> List[str]:
        """
        Get required permissions for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            List of required permission scopes
            
        Raises:
            KeyError: If tool doesn't exist
        """
        tool = self._tools.get(tool_name)
        if not tool:
            raise KeyError(f"Tool '{tool_name}' not found in registry")
        
        return tool.required_permissions
    
    def get_tools_by_permission(self, permission: str) -> List[ToolDefinition]:
        """
        Find tools that require a specific permission.
        
        Args:
            permission: Permission scope to search for
            
        Returns:
            List of tools requiring this permission
        """
        return [
            t for t in self._tools.values()
            if permission in t.required_permissions
        ]
    
    def validate_inputs(self, tool_name: str, inputs: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate inputs against tool's input schema.
        
        Args:
            tool_name: Name of the tool
            inputs: Input dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
        
        schema = tool.input_schema
        
        # Check required fields
        for required_field in schema.required:
            if required_field not in inputs:
                return False, f"Missing required field: {required_field}"
        
        # Basic type validation (expand as needed)
        for field, value in inputs.items():
            if field in schema.properties:
                expected_type = schema.properties[field].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    return False, f"Field '{field}' has invalid type, expected {expected_type}"
        
        return True, None
    
    def _check_type(self, value, expected_type: str) -> bool:
        """Check if value matches expected JSON Schema type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        return True  # Unknown types pass through
    
    def _register_default_tools(self) -> None:
        """Register built-in tools for Google Workspace and internal processing."""
        
        # =================================================================
        # Google Sheets Tools
        # =================================================================
        
        self.register_tool(ToolDefinition(
            tool_name="google_sheets_create",
            description="Create a new Google Spreadsheet",
            category=ToolCategory.DOCUMENT,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.sheets.write", "google.drive.write"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Spreadsheet title"},
                    "sheets": {"type": "array", "description": "Sheet names to create"}
                },
                "required": ["title"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string"},
                    "spreadsheet_url": {"type": "string"}
                }
            }
        ))
        
        self.register_tool(ToolDefinition(
            tool_name="google_sheets_read",
            description="Read data from a Google Spreadsheet",
            category=ToolCategory.DATA,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.sheets.read"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string"},
                    "range": {"type": "string", "description": "A1 notation range"}
                },
                "required": ["spreadsheet_id", "range"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "values": {"type": "array"},
                    "range": {"type": "string"}
                }
            }
        ))
        
        self.register_tool(ToolDefinition(
            tool_name="google_sheets_append_row",
            description="Append a row to a Google Spreadsheet",
            category=ToolCategory.DATA,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.sheets.write"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string"},
                    "sheet": {"type": "string", "description": "Sheet name"},
                    "values": {"type": "array", "description": "Row values to append"}
                },
                "required": ["spreadsheet_id", "sheet", "values"]
            }
        ))
        
        self.register_tool(ToolDefinition(
            tool_name="google_sheets_update",
            description="Update cells in a Google Spreadsheet",
            category=ToolCategory.DATA,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.sheets.write"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string"},
                    "range": {"type": "string"},
                    "values": {"type": "array"}
                },
                "required": ["spreadsheet_id", "range", "values"]
            }
        ))
        
        # =================================================================
        # Google Slides Tools
        # =================================================================
        
        self.register_tool(ToolDefinition(
            tool_name="google_slides_create",
            description="Create a new Google Slides presentation",
            category=ToolCategory.DOCUMENT,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.slides.write", "google.drive.write"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"}
                },
                "required": ["title"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "presentation_id": {"type": "string"},
                    "presentation_url": {"type": "string"}
                }
            }
        ))
        
        self.register_tool(ToolDefinition(
            tool_name="google_slides_add_slide",
            description="Add a slide to a Google Slides presentation",
            category=ToolCategory.DOCUMENT,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.slides.write"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "presentation_id": {"type": "string"},
                    "layout": {"type": "string", "description": "Slide layout type"},
                    "title": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["presentation_id"]
            }
        ))
        
        # =================================================================
        # Google Drive Tools
        # =================================================================
        
        self.register_tool(ToolDefinition(
            tool_name="google_drive_share",
            description="Share a Google Drive file with users",
            category=ToolCategory.COMMUNICATION,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.drive.write"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "email": {"type": "string"},
                    "role": {"type": "string", "description": "reader, writer, or commenter"}
                },
                "required": ["file_id", "email", "role"]
            }
        ))
        
        self.register_tool(ToolDefinition(
            tool_name="google_drive_list",
            description="List files in Google Drive",
            category=ToolCategory.DATA,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.drive.read"],
            timeout_seconds=30,
            retry_policy="exponential",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "page_size": {"type": "integer"}
                },
                "required": []
            }
        ))
        
        # =================================================================
        # Internal Data Processing Tools
        # =================================================================
        
        self.register_tool(ToolDefinition(
            tool_name="data_transform",
            description="Transform data using Python code in sandbox",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
            required_permissions=[],
            timeout_seconds=60,
            retry_policy="none",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python transformation code"},
                    "input_data": {"type": "object", "description": "Data to transform"}
                },
                "required": ["code", "input_data"]
            }
        ))
        
        self.register_tool(ToolDefinition(
            tool_name="text_processing",
            description="Process and analyze text data",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
            required_permissions=[],
            timeout_seconds=30,
            retry_policy="none",
            cost_level="low",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "operation": {"type": "string", "description": "summarize, extract, format"}
                },
                "required": ["text", "operation"]
            }
        ))
        
        logger.info(f"Registered {len(self._tools)} default tools")
    
    @property
    def tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self._tools)
    
    @property
    def is_initialized(self) -> bool:
        """Check if registry is initialized."""
        return self._initialized


# Singleton instance
_registry: Optional[ToolRegistry] = None


async def get_tool_registry() -> ToolRegistry:
    """Get or create the tool registry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        await _registry.initialize()
    return _registry
