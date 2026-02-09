"""Internal Tool Adapter - Sandboxed data processing and transformation tools.

This adapter handles internal tools that process data in a secure sandbox
without external API calls.
"""

import logging
import time
from typing import Dict, Any

from .base import BaseToolAdapter
from ..types import (
    ActionStep, AdapterResult, ExecutionContext, ToolVendor, Artifact
)

logger = logging.getLogger(__name__)


class InternalToolAdapter(BaseToolAdapter):
    """
    Adapter for internal/sandboxed tools.
    
    Supports:
    - data_transform: Python code execution in sandbox
    - text_processing: Text analysis and manipulation
    - file_conversion: Format conversions
    
    Security:
    - All code execution happens in isolated subprocess
    - Resource limits enforced
    - No network access
    """
    
    SUPPORTED_TOOLS = [
        "data_transform",
        "text_processing",
        "file_conversion",
    ]
    
    def __init__(self):
        super().__init__()
        self.name = "internal"
        self.vendor = ToolVendor.INTERNAL
        self._sandbox = None
    
    async def initialize(self) -> None:
        """Initialize the adapter."""
        # Import sandbox lazily to avoid circular imports
        from ..sandbox import ExecutionSandbox
        self._sandbox = ExecutionSandbox()
        await self._sandbox.initialize()
        
        self._available = True
        self._initialized = True
        logger.info("Internal tool adapter initialized")
    
    async def execute(
        self,
        action: ActionStep,
        context: ExecutionContext,
    ) -> AdapterResult:
        """Execute an internal tool action."""
        start_time = time.time()
        
        tool_name = action.tool
        inputs = action.inputs
        
        try:
            if tool_name == "data_transform":
                result = await self._data_transform(inputs, context)
            elif tool_name == "text_processing":
                result = await self._text_processing(inputs, context)
            elif tool_name == "file_conversion":
                result = await self._file_conversion(inputs, context)
            else:
                return AdapterResult(
                    success=False,
                    error=f"Unknown internal tool: {tool_name}",
                    error_code="UNKNOWN_TOOL",
                    latency_ms=int((time.time() - start_time) * 1000)
                )
            
            result.latency_ms = int((time.time() - start_time) * 1000)
            return result
            
        except Exception as e:
            logger.exception(f"Error in internal adapter: {e}")
            return AdapterResult(
                success=False,
                error=str(e),
                error_code="INTERNAL_ERROR",
                latency_ms=int((time.time() - start_time) * 1000)
            )
    
    async def health_check(self) -> bool:
        """Check if internal tools are available."""
        return self._sandbox is not None and self._sandbox.is_available()
    
    def supports_tool(self, tool_name: str) -> bool:
        """Check if this adapter supports a tool."""
        return tool_name in self.SUPPORTED_TOOLS
    
    async def _data_transform(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> AdapterResult:
        """
        Transform data using Python code in sandbox.
        
        The code receives `input_data` as a variable and should
        set `output_data` with the result.
        """
        code = inputs.get("code", "")
        input_data = inputs.get("input_data", {})
        
        if not code:
            return AdapterResult(
                success=False,
                error="No transformation code provided",
                error_code="MISSING_CODE"
            )
        
        # Wrap code to capture output
        wrapped_code = f"""
input_data = {repr(input_data)}
output_data = None

{code}

# Result captured from output_data variable
__result__ = output_data
"""
        
        # Execute in sandbox
        from ..types import ResourceLimits
        limits = ResourceLimits(
            max_cpu_seconds=10,
            max_memory_mb=128,
            timeout_seconds=30,
            allow_network=False
        )
        
        sandbox_result = await self._sandbox.execute_safely(
            wrapped_code,
            {},
            limits
        )
        
        if not sandbox_result.success:
            return AdapterResult(
                success=False,
                error=sandbox_result.error or "Sandbox execution failed",
                error_code="SANDBOX_ERROR"
            )
        
        return AdapterResult(
            success=True,
            data={
                "output": sandbox_result.output,
                "execution_time_ms": sandbox_result.execution_time_ms,
            }
        )
    
    async def _text_processing(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> AdapterResult:
        """
        Process text using built-in operations.
        
        Operations:
        - summarize: Create a summary of the text
        - extract: Extract key information
        - format: Format text according to template
        - count: Count words/characters/sentences
        """
        text = inputs.get("text", "")
        operation = inputs.get("operation", "count")
        
        if not text:
            return AdapterResult(
                success=False,
                error="No text provided",
                error_code="MISSING_INPUT"
            )
        
        if operation == "count":
            words = len(text.split())
            chars = len(text)
            sentences = text.count('.') + text.count('!') + text.count('?')
            
            return AdapterResult(
                success=True,
                data={
                    "words": words,
                    "characters": chars,
                    "sentences": sentences,
                }
            )
        
        elif operation == "extract":
            # Extract basic patterns (emails, URLs, numbers)
            import re
            
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
            urls = re.findall(r'https?://\S+', text)
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
            
            return AdapterResult(
                success=True,
                data={
                    "emails": emails,
                    "urls": urls,
                    "numbers": numbers,
                }
            )
        
        elif operation == "format":
            template = inputs.get("template", "{text}")
            try:
                formatted = template.format(text=text, **inputs)
                return AdapterResult(
                    success=True,
                    data={"formatted": formatted}
                )
            except KeyError as e:
                return AdapterResult(
                    success=False,
                    error=f"Missing template variable: {e}",
                    error_code="TEMPLATE_ERROR"
                )
        
        elif operation == "summarize":
            # Basic extractive summary (first N sentences)
            sentences = text.replace('!', '.').replace('?', '.').split('.')
            sentences = [s.strip() for s in sentences if s.strip()]
            max_sentences = inputs.get("max_sentences", 3)
            summary = '. '.join(sentences[:max_sentences])
            if summary and not summary.endswith('.'):
                summary += '.'
            
            return AdapterResult(
                success=True,
                data={
                    "summary": summary,
                    "original_sentences": len(sentences),
                    "summary_sentences": min(len(sentences), max_sentences),
                }
            )
        
        else:
            return AdapterResult(
                success=False,
                error=f"Unknown operation: {operation}",
                error_code="UNKNOWN_OPERATION"
            )
    
    async def _file_conversion(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> AdapterResult:
        """
        Convert data between formats.
        
        Supported conversions:
        - json_to_csv
        - csv_to_json
        - json_to_yaml
        - yaml_to_json
        """
        import json
        import csv
        import io
        
        data = inputs.get("data")
        conversion = inputs.get("conversion", "")
        
        if not data:
            return AdapterResult(
                success=False,
                error="No data provided",
                error_code="MISSING_INPUT"
            )
        
        try:
            if conversion == "json_to_csv":
                # Assume data is list of dicts
                if isinstance(data, str):
                    data = json.loads(data)
                
                if not isinstance(data, list) or not data:
                    return AdapterResult(
                        success=False,
                        error="Data must be a non-empty list of objects",
                        error_code="INVALID_DATA"
                    )
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                
                return AdapterResult(
                    success=True,
                    data={"csv": output.getvalue(), "rows": len(data)}
                )
            
            elif conversion == "csv_to_json":
                if isinstance(data, str):
                    reader = csv.DictReader(io.StringIO(data))
                    rows = list(reader)
                else:
                    rows = data
                
                return AdapterResult(
                    success=True,
                    data={"json": rows, "rows": len(rows)}
                )
            
            elif conversion == "json_to_yaml":
                try:
                    import yaml
                    if isinstance(data, str):
                        data = json.loads(data)
                    yaml_str = yaml.dump(data, default_flow_style=False)
                    return AdapterResult(
                        success=True,
                        data={"yaml": yaml_str}
                    )
                except ImportError:
                    return AdapterResult(
                        success=False,
                        error="PyYAML not installed",
                        error_code="MISSING_DEPENDENCY"
                    )
            
            elif conversion == "yaml_to_json":
                try:
                    import yaml
                    if isinstance(data, str):
                        data = yaml.safe_load(data)
                    return AdapterResult(
                        success=True,
                        data={"json": data}
                    )
                except ImportError:
                    return AdapterResult(
                        success=False,
                        error="PyYAML not installed",
                        error_code="MISSING_DEPENDENCY"
                    )
            
            else:
                return AdapterResult(
                    success=False,
                    error=f"Unknown conversion: {conversion}",
                    error_code="UNKNOWN_CONVERSION"
                )
                
        except Exception as e:
            return AdapterResult(
                success=False,
                error=f"Conversion failed: {str(e)}",
                error_code="CONVERSION_ERROR"
            )
