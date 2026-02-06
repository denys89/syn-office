import logging
from typing import Optional
import httpx

from config import get_settings
from models import ExecuteRequest, ExecuteResponse, TaskStatus, AgentContext
from database import get_database
from llm_client import get_llm_client

logger = logging.getLogger(__name__)

# Lazy import to avoid startup failures if Qdrant is not available
_qdrant_client = None
_qdrant_available = True


async def _get_qdrant():
    """Get Qdrant client with lazy initialization and error handling."""
    global _qdrant_client, _qdrant_available
    
    if not _qdrant_available:
        return None
    
    if _qdrant_client is None:
        try:
            from qdrant_service import get_qdrant_client
            _qdrant_client = await get_qdrant_client()
        except Exception as e:
            logger.warning(f"Qdrant not available, using PostgreSQL-only memory: {e}")
            _qdrant_available = False
            return None
    
    return _qdrant_client


class Orchestrator:
    """Main orchestrator for agent task execution."""
    
    def __init__(self):
        self.db = get_database()
        self.llm = get_llm_client()
        self.settings = get_settings()
    
    async def execute_task(self, request: ExecuteRequest) -> ExecuteResponse:
        """
        Execute a task by:
        1. Loading agent context (with semantic memory search)
        2. Generating LLM response
        3. Saving response and updating task
        4. Optionally extracting and saving memories
        """
        try:
            # Update status to thinking
            await self.db.update_task_status(request.task_id, TaskStatus.THINKING.value)
            
            # Load agent context
            context = await self._load_agent_context(request)
            if context is None:
                return ExecuteResponse(
                    task_id=request.task_id,
                    status=TaskStatus.FAILED,
                    error="Agent not found",
                )
            
            # Update status to working
            await self.db.update_task_status(request.task_id, TaskStatus.WORKING.value)
            
            # Generate response
            output, token_usage = await self.llm.generate(context, request.input)
            
            # Update task with output
            await self.db.update_task_status(
                request.task_id, 
                TaskStatus.DONE.value, 
                output=output
            )
            
            # Save response as agent message
            await self._save_agent_response(request, output)
            
            # Broadcast to WebSocket (via backend)
            await self._notify_backend(request, output)
            
            return ExecuteResponse(
                task_id=request.task_id,
                status=TaskStatus.DONE,
                output=output,
                token_usage=token_usage,
            )
            
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            await self.db.update_task_status(
                request.task_id, 
                TaskStatus.FAILED.value, 
                error=str(e)
            )
            return ExecuteResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
            )
    
    async def _load_agent_context(self, request: ExecuteRequest) -> Optional[AgentContext]:
        """Load full agent context for LLM, including semantic memory search."""
        # Get agent info
        agent = await self.db.get_agent(request.agent_id)
        if not agent:
            return None
        
        # Get conversation history
        history = await self.db.get_conversation_history(request.conversation_id)
        
        # Get memories - try semantic search first, fall back to PostgreSQL
        memories = await self._get_relevant_memories(request.agent_id, request.input)
        
        # Determine name and prompt
        agent_name = agent.get("custom_name") or agent.get("template_name", "Agent")
        system_prompt = agent.get("custom_system_prompt") or agent.get("template_system_prompt", "")
        
        return AgentContext(
            agent_id=request.agent_id,
            agent_name=agent_name,
            agent_role=agent.get("template_role", "Assistant"),
            system_prompt=system_prompt,
            conversation_history=history,
            memories=memories,
        )
    
    async def _get_relevant_memories(self, agent_id: str, query: str) -> list[str]:
        """
        Get relevant memories using semantic search if available,
        otherwise fall back to PostgreSQL key-value memories.
        """
        # Try Qdrant semantic search first
        qdrant = await _get_qdrant()
        if qdrant:
            try:
                semantic_memories = await qdrant.search_memories(
                    query=query,
                    agent_id=agent_id,
                    limit=5,
                    min_score=0.4,  # Lower threshold to get more results
                )
                if semantic_memories:
                    # Format memories with importance indicator
                    formatted = []
                    for mem in semantic_memories:
                        importance = "⭐" if mem["importance"] > 0.7 else ""
                        formatted.append(f"{mem['key']}: {mem['value']} {importance}".strip())
                    logger.debug(f"Found {len(formatted)} semantic memories for agent {agent_id}")
                    return formatted
            except Exception as e:
                logger.warning(f"Semantic memory search failed, using fallback: {e}")
        
        # Fall back to PostgreSQL memories
        return await self.db.get_agent_memories(agent_id)
    
    async def _save_agent_response(self, request: ExecuteRequest, output: str):
        """Save agent response as a message in the conversation."""
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages (id, office_id, conversation_id, sender_type, sender_id, content, metadata, created_at)
                VALUES (gen_random_uuid(), $1, $2, 'agent', $3, $4, '{}', NOW())
                """,
                request.office_id,
                request.conversation_id,
                request.agent_id,
                output,
            )
    
    async def _notify_backend(self, request: ExecuteRequest, output: str):
        """Notify the backend about the completed task (for WebSocket broadcast)."""
        try:
            api_key = self.settings.internal_api_key
            logger.info(f"Notifying backend with API key: {api_key[:10]}... (length: {len(api_key)})")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.settings.backend_url}/api/v1/internal/task-complete",
                    json={
                        "task_id": request.task_id,
                        "conversation_id": request.conversation_id,
                        "agent_id": request.agent_id,
                        "output": output,
                    },
                    headers={
                        "X-Internal-API-Key": api_key,
                    },
                    timeout=5.0,
                )
                logger.info(f"Backend response status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Backend response: {response.text}")
        except Exception as e:
            # Log but don't fail - message is already saved
            logger.warning(f"Failed to notify backend: {e}")


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get the orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator

