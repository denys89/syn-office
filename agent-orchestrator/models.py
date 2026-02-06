from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum
from uuid import UUID


class TaskStatus(str, Enum):
    PENDING = "pending"
    THINKING = "thinking"
    WORKING = "working"
    DONE = "done"
    FAILED = "failed"


class ExecuteRequest(BaseModel):
    """Request to execute a task."""
    task_id: str
    agent_id: str
    office_id: str
    conversation_id: str
    input: str


class ExecuteResponse(BaseModel):
    """Response from task execution."""
    task_id: str
    status: TaskStatus
    output: Optional[str] = None
    error: Optional[str] = None
    token_usage: Dict[str, int] = {}


class AgentContext(BaseModel):
    """Context for agent execution."""
    agent_id: str
    agent_name: str
    agent_role: str
    system_prompt: str
    conversation_history: list[Dict[str, Any]] = []
    memories: list[str] = []


class Message(BaseModel):
    """A chat message."""
    role: str  # "system", "user", "assistant"
    content: str


class AgentMemory(BaseModel):
    """Agent memory entry."""
    key: str
    value: str
    metadata: Dict[str, Any] = {}
