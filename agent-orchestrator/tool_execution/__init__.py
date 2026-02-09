"""Tool Execution Layer - Production-grade tool execution for AI agents.

This package provides:
- Tool Registry: Central catalog of executable tools
- Tool Adapters: Vendor-specific API integrations
- Execution Orchestrator: Multi-step execution coordination
- Security Gateway: Permission and access control
- Quota Manager: Rate limiting and cost control
- Execution Sandbox: Isolated code execution
- Result Normalizer: Unified response format
"""

from .types import (
    # Enums
    ToolCategory,
    ToolVendor,
    CostLevel,
    RetryPolicy,
    ExecutionStatus,
    FailureHandling,
    PermissionStatus,
    # Tool Definition
    ToolDefinition,
    ToolInputSchema,
    ToolOutputSchema,
    # Action Plans
    ActionStep,
    ActionPlan,
    # Results
    Artifact,
    StepResult,
    ExecutionResult,
    AdapterResult,
    # Security
    PermissionScope,
    PermissionResult,
    # Quotas
    QuotaConfig,
    UsageRecord,
    QuotaCheckResult,
    QuotaStatus,
    # Context
    ExecutionContext,
    # Sandbox
    ResourceLimits,
    SandboxResult,
)

from .tool_registry import ToolRegistry, get_tool_registry
from .security_gateway import SecurityGateway, get_security_gateway
from .quota_manager import QuotaManager, get_quota_manager
from .sandbox import ExecutionSandbox
from .result_normalizer import ResultNormalizer, get_result_normalizer
from .execution_orchestrator import ExecutionOrchestrator, get_execution_orchestrator

# Adapters
from .adapters import (
    BaseToolAdapter,
    GoogleWorkspaceAdapter,
    InternalToolAdapter,
)

from .schema_generator import ToolSchemaGenerator
from .plan_parser import ActionPlanParser

__all__ = [
    # Enums
    "ToolCategory",
    "ToolVendor",
    "CostLevel",
    "RetryPolicy",
    "ExecutionStatus",
    "FailureHandling",
    "PermissionStatus",
    # Tool Definition
    "ToolDefinition",
    "ToolInputSchema",
    "ToolOutputSchema",
    # Action Plans
    "ActionStep",
    "ActionPlan",
    # Results
    "Artifact",
    "StepResult",
    "ExecutionResult",
    "AdapterResult",
    # Security
    "PermissionScope",
    "PermissionResult",
    # Quotas
    "QuotaConfig",
    "UsageRecord",
    "QuotaCheckResult",
    "QuotaStatus",
    # Context
    "ExecutionContext",
    # Sandbox
    "ResourceLimits",
    "SandboxResult",
    # Core Components
    "ToolRegistry",
    "get_tool_registry",
    "SecurityGateway",
    "get_security_gateway",
    "QuotaManager",
    "get_quota_manager",
    "ExecutionSandbox",
    "ResultNormalizer",
    "get_result_normalizer",
    "ExecutionOrchestrator",
    "get_execution_orchestrator",
    # Adapters
    "BaseToolAdapter",
    "GoogleWorkspaceAdapter",
    "InternalToolAdapter",
    # Utilities
    "ToolSchemaGenerator",
    "ActionPlanParser",
]

