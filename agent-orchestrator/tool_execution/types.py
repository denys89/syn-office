"""Tool Execution Layer types and data models.

This module defines all Pydantic models for the Tool Execution Layer:
- Tool definitions and metadata
- Action plans and steps
- Execution results and artifacts
- Permission and quota configurations
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime
import uuid


# =============================================================================
# Enums
# =============================================================================

class ToolCategory(str, Enum):
    """Category classification for tools."""
    DATA = "data"
    COMMUNICATION = "communication"
    DOCUMENT = "document"
    SYSTEM = "system"
    INTEGRATION = "integration"


class ToolVendor(str, Enum):
    """Supported tool vendors/providers."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    AWS = "aws"
    INTERNAL = "internal"
    CUSTOM = "custom"


class CostLevel(str, Enum):
    """Cost tier for tools."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RetryPolicy(str, Enum):
    """Retry policy for tool execution."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class ExecutionStatus(str, Enum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    BLOCKED = "blocked"


class FailureHandling(str, Enum):
    """How to handle step failures."""
    STOP = "stop"
    CONTINUE = "continue"
    RETRY = "retry"
    FALLBACK = "fallback"


class PermissionStatus(str, Enum):
    """Result of permission check."""
    GRANTED = "granted"
    DENIED = "denied"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"


# =============================================================================
# Tool Definition Models
# =============================================================================

class ToolInputSchema(BaseModel):
    """JSON Schema for tool inputs."""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolOutputSchema(BaseModel):
    """JSON Schema for tool outputs."""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Definition of an executable tool in the registry.
    
    This is the central metadata structure for all tools.
    Planning Layer selects tools exclusively from registered definitions.
    """
    tool_name: str
    description: str
    category: ToolCategory
    input_schema: ToolInputSchema = Field(default_factory=ToolInputSchema)
    output_schema: ToolOutputSchema = Field(default_factory=ToolOutputSchema)
    required_permissions: List[str] = Field(default_factory=list)
    vendor: ToolVendor
    timeout_seconds: int = 30
    retry_policy: RetryPolicy = RetryPolicy.NONE
    max_retries: int = 3
    cost_level: CostLevel = CostLevel.LOW
    available: bool = True
    
    # Rate limit hints
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None


# =============================================================================
# Action Plan Models
# =============================================================================

class ActionStep(BaseModel):
    """Single step in an action plan."""
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool: str  # Tool name from registry
    inputs: Dict[str, Any] = Field(default_factory=dict)
    timeout_override: Optional[int] = None
    failure_handling: FailureHandling = FailureHandling.STOP
    depends_on: List[str] = Field(default_factory=list)  # step_ids this depends on
    
    # Runtime fields (populated during execution)
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ActionPlan(BaseModel):
    """Multi-step execution plan from the Planning Layer."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    steps: List[ActionStep]
    context: Dict[str, Any] = Field(default_factory=dict)  # Shared context across steps
    parallel_execution: bool = False  # If true, execute independent steps in parallel
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None  # User/agent ID
    office_id: Optional[str] = None


# =============================================================================
# Execution Result Models
# =============================================================================

class Artifact(BaseModel):
    """Output artifact from tool execution."""
    type: str  # spreadsheet, document, presentation, file, data
    url: Optional[str] = None
    content: Optional[Any] = None  # Raw content if no URL
    metadata: Dict[str, Any] = Field(default_factory=dict)
    mime_type: Optional[str] = None


class StepResult(BaseModel):
    """Result of a single step execution."""
    step_id: str
    tool: str
    status: ExecutionStatus
    artifacts: List[Artifact] = Field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: int = 0
    retry_count: int = 0


class ExecutionResult(BaseModel):
    """Normalized result of entire plan execution.
    
    This is the unified response format for all tool executions,
    consumed by Result Validation Layer, UI, and Audit systems.
    """
    status: ExecutionStatus
    execution_id: str
    artifacts: List[Artifact] = Field(default_factory=list)
    message: str  # Human-readable summary
    errors: List[str] = Field(default_factory=list)
    step_results: List[StepResult] = Field(default_factory=list)
    
    # Metrics
    total_latency_ms: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# =============================================================================
# Permission & Security Models
# =============================================================================

class PermissionScope(BaseModel):
    """User-granted permission scope."""
    user_id: str
    office_id: str
    granted_scopes: List[str] = Field(default_factory=list)
    oauth_tokens: Dict[str, str] = Field(default_factory=dict)  # vendor -> token
    token_expiry: Dict[str, datetime] = Field(default_factory=dict)


class PermissionResult(BaseModel):
    """Result of permission check."""
    status: PermissionStatus
    allowed: bool
    missing_permissions: List[str] = Field(default_factory=list)
    reason: Optional[str] = None


# =============================================================================
# Quota & Rate Limit Models
# =============================================================================

class QuotaConfig(BaseModel):
    """Quota configuration for a vendor/tool."""
    vendor: ToolVendor
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    concurrent_requests: int = 10


class UsageRecord(BaseModel):
    """Record of API usage."""
    vendor: ToolVendor
    tool: str
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_count: int = 1
    cost_estimate: float = 0.0


class QuotaCheckResult(BaseModel):
    """Result of quota check."""
    allowed: bool
    reason: Optional[str] = None
    current_usage: int = 0
    limit: int = 0
    reset_at: Optional[datetime] = None
    cooldown_seconds: int = 0


class QuotaStatus(BaseModel):
    """Current quota status for a user/vendor."""
    vendor: ToolVendor
    user_id: str
    minute_remaining: int = 0
    hour_remaining: int = 0
    day_remaining: int = 0
    percentage_used: float = 0.0


# =============================================================================
# Execution Context
# =============================================================================

class ExecutionContext(BaseModel):
    """Context passed through tool execution."""
    user_id: str
    office_id: str
    permissions: PermissionScope
    shared_data: Dict[str, Any] = Field(default_factory=dict)  # Data shared between steps
    dry_run: bool = False  # If true, validate but don't execute


# =============================================================================
# Adapter Models
# =============================================================================

class AdapterResult(BaseModel):
    """Result from a tool adapter."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    artifacts: List[Artifact] = Field(default_factory=list)
    error: Optional[str] = None
    error_code: Optional[str] = None
    latency_ms: int = 0
    raw_response: Optional[Any] = None  # Vendor-specific response for debugging


# =============================================================================
# Sandbox Models
# =============================================================================

class ResourceLimits(BaseModel):
    """Resource limits for sandbox execution."""
    max_cpu_seconds: int = 10
    max_memory_mb: int = 256
    max_output_size_kb: int = 1024
    timeout_seconds: int = 30
    allow_network: bool = False
    allowed_hosts: List[str] = Field(default_factory=list)


class SandboxResult(BaseModel):
    """Result from sandbox execution."""
    success: bool
    output: Optional[Any] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    execution_time_ms: int = 0
    memory_used_mb: float = 0.0
