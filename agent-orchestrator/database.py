import asyncpg
from typing import Optional, Dict, Any
import logging

from config import get_settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create database connection pool."""
        settings = get_settings()
        self.pool = await asyncpg.create_pool(settings.database_url)
        logger.info("Database connected")
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database disconnected")
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent with template information."""
        query = """
            SELECT 
                a.id, a.office_id, a.template_id, a.custom_name, a.custom_system_prompt,
                t.name as template_name, t.role as template_role, t.system_prompt as template_system_prompt
            FROM agents a
            JOIN agent_templates t ON a.template_id = t.id
            WHERE a.id = $1 AND a.is_active = true
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, agent_id)
            if row:
                return dict(row)
            return None
    
    async def get_conversation_history(
        self, 
        conversation_id: str, 
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """Get recent messages from a conversation."""
        query = """
            SELECT id, sender_type, sender_id, content, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, conversation_id, limit)
            # Reverse to get chronological order
            return [dict(row) for row in reversed(rows)]
    
    async def get_agent_memories(self, agent_id: str) -> list[str]:
        """Get agent's long-term memories."""
        query = """
            SELECT key, value
            FROM agent_memories
            WHERE agent_id = $1
            ORDER BY updated_at DESC
            LIMIT 20
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, agent_id)
            return [f"{row['key']}: {row['value']}" for row in rows]
    
    async def save_agent_memory(
        self, 
        office_id: str,
        agent_id: str, 
        key: str, 
        value: str
    ):
        """Save or update an agent memory."""
        query = """
            INSERT INTO agent_memories (id, office_id, agent_id, key, value, created_at, updated_at)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, NOW(), NOW())
            ON CONFLICT (agent_id, key) DO UPDATE SET value = $4, updated_at = NOW()
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, office_id, agent_id, key, value)
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        output: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Update task status in the database."""
        query = """
            UPDATE tasks
            SET status = $2::VARCHAR, 
                output = COALESCE($3::TEXT, output), 
                error = COALESCE($4::TEXT, error),
                completed_at = CASE WHEN $2 IN ('done', 'failed') THEN NOW() ELSE completed_at END
            WHERE id = $1::UUID
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, task_id, status, output, error)


# Singleton instance
_database: Optional[Database] = None


def get_database() -> Database:
    """Get the database singleton."""
    global _database
    if _database is None:
        _database = Database()
    return _database
