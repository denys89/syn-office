"""Base Tool Adapter - Abstract interface for vendor-specific implementations.

All tool adapters must implement this interface to support
the execution orchestrator's execution flow.
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

from ..types import ActionStep, AdapterResult, ExecutionContext, ToolVendor

logger = logging.getLogger(__name__)


class BaseToolAdapter(ABC):
    """
    Abstract base class for tool adapters.
    
    Adapters translate generic AI actions into vendor-specific API calls.
    
    Responsibilities:
    - API request construction
    - API authentication injection
    - Vendor-specific response handling
    
    Constraints:
    - No business logic
    - No permission decisions (handled by Security Gateway)
    - No retries (handled by Execution Orchestrator)
    """
    
    def __init__(self):
        self.name: str = "base"
        self.vendor: ToolVendor = ToolVendor.INTERNAL
        self._initialized: bool = False
        self._available: bool = False
    
    async def initialize(self) -> None:
        """
        Initialize the adapter.
        
        Override this to perform async initialization
        (API client setup, credential validation, etc).
        """
        self._initialized = True
        logger.info(f"Adapter {self.name} initialized")
    
    @abstractmethod
    async def execute(
        self,
        action: ActionStep,
        context: ExecutionContext,
    ) -> AdapterResult:
        """
        Execute a tool action.
        
        Args:
            action: The action step to execute
            context: Execution context with user info, permissions, etc.
            
        Returns:
            AdapterResult with success status, data, and any artifacts
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the adapter and its backend service are healthy.
        
        Returns:
            True if adapter is healthy and ready to accept requests
        """
        pass
    
    @abstractmethod
    def supports_tool(self, tool_name: str) -> bool:
        """
        Check if this adapter supports a specific tool.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if this adapter can execute the tool
        """
        pass
    
    def is_available(self) -> bool:
        """Check if adapter is available."""
        return self._available
    
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._initialized
    
    async def shutdown(self) -> None:
        """
        Graceful shutdown of the adapter.
        
        Override to clean up resources, close connections, etc.
        """
        self._initialized = False
        self._available = False
        logger.info(f"Adapter {self.name} shut down")
