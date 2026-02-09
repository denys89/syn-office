from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .types import ToolDefinition

class ToolSchemaGenerator:
    """Generates JSON schemas for tools to be used in LLM prompts."""

    @staticmethod
    def generate_schema(tool: ToolDefinition) -> Dict[str, Any]:
        """
        Convert a ToolDefinition into a JSON schema dictionary.
        This follows the OpenAI function calling schema as a standard.
        """
        # Ensure parameters schema is clean
        # input_schema is a ToolInputSchema model
        parameters = tool.input_schema.model_dump()
        
        # We can implement specific filtering or simplification here if needed
        # e.g. removing internal-only metadata not relevant to the LLM
        
        return {
            "name": tool.tool_name,
            "description": tool.description,
            "parameters": parameters
        }

    @staticmethod
    def generate_schemas(tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """Generate schemas for a list of tools."""
        return [ToolSchemaGenerator.generate_schema(tool) for tool in tools]

    @staticmethod
    def generate_prompt_text(tools: List[ToolDefinition]) -> str:
        """
        Generate a text representation suitable for system prompts that don't support function calling API natively.
        """
        schemas = ToolSchemaGenerator.generate_schemas(tools)
        import json
        return json.dumps(schemas, indent=2)
