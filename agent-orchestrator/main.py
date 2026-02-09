from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import logging

from config import get_settings
from database import get_database
from orchestrator import get_orchestrator
from models import ExecuteRequest, ExecuteResponse, TaskStatus
from tool_execution import ActionPlan, ExecutionResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Synoffice Agent Orchestrator...")
    db = get_database()
    await db.connect()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await db.disconnect()


app = FastAPI(
    title="Synoffice Agent Orchestrator",
    description="AI Agent Orchestrator for Synoffice digital office",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "orchestrator"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute_task(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """
    Execute an agent task.
    
    This endpoint receives task requests from the backend and processes them
    asynchronously using the appropriate agent.
    """
    logger.info(f"Received task: {request.task_id} for agent: {request.agent_id}")
    
    orchestrator = get_orchestrator()
    
    # Execute task (this is async but we await it here for simplicity)
    # In production, you might want to use background tasks or a queue
    result = await orchestrator.execute_task(request)
    
    return result


@app.post("/execute-async")
async def execute_task_async(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """
    Queue a task for async execution.
    
    Returns immediately and processes the task in the background.
    """
    logger.info(f"Queuing task: {request.task_id} for agent: {request.agent_id}")
    
    orchestrator = get_orchestrator()
    background_tasks.add_task(orchestrator.execute_task, request)
    
    return {
        "task_id": request.task_id,
        "status": "queued",
        "message": "Task queued for processing",
    }


@app.get("/agents")
async def list_agent_templates():
    """List available agent templates."""
    db = get_database()
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, role, skill_tags FROM agent_templates ORDER BY name"
        )
        return {
            "templates": [dict(row) for row in rows]
        }


@app.post("/execute-tools", response_model=ExecutionResult)
async def execute_tools(plan: ActionPlan, user_id: str = "test_user", office_id: str = "test_office"):
    """
    Directly execute a set of tools defined in an Action Plan.
    
    This endpoint is primarily for:
    1. Testing tool execution independently of LLM
    2. executing pre-defined deterministic workflows
    3. Retrying failed tool steps
    """
    logger.info(f"Received tool execution plan: {plan.execution_id} with {len(plan.steps)} steps")
    
    orchestrator = get_orchestrator()
    result = await orchestrator.execute_tool_plan(plan, user_id, office_id)
    
    return result


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
