"""Metrics - Observability and execution metrics persistence to PostgreSQL."""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
import asyncpg

from model_selection.types import ModelExecutionMetrics

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Service for persisting and querying model execution metrics.
    
    Stores metrics in PostgreSQL for analytics and future optimization.
    """

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        self.pool = pool
        self._initialized = False

    async def initialize(self, pool: asyncpg.Pool) -> None:
        """Initialize with database pool and create table if needed."""
        self.pool = pool
        await self._ensure_table()
        self._initialized = True
        logger.info("Metrics service initialized")

    async def _ensure_table(self) -> None:
        """Create metrics table if it doesn't exist."""
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS model_execution_metrics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task_id VARCHAR(255) NOT NULL,
                    agent_id VARCHAR(255) NOT NULL,
                    selected_model VARCHAR(255) NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    alternatives_considered TEXT[],
                    capability_match_score FLOAT,
                    total_score FLOAT,
                    latency_ms INTEGER,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    estimated_cost FLOAT,
                    success BOOLEAN NOT NULL,
                    error TEXT,
                    fallback_used BOOLEAN DEFAULT FALSE,
                    fallback_model VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_metrics_task_id ON model_execution_metrics(task_id);
                CREATE INDEX IF NOT EXISTS idx_metrics_agent_id ON model_execution_metrics(agent_id);
                CREATE INDEX IF NOT EXISTS idx_metrics_model ON model_execution_metrics(selected_model);
                CREATE INDEX IF NOT EXISTS idx_metrics_created ON model_execution_metrics(created_at);
            """)
            logger.debug("Metrics table ensured")

    async def save(self, metrics: ModelExecutionMetrics) -> str:
        """
        Save execution metrics to database.
        
        Returns:
            The generated metrics ID
        """
        if not self.pool:
            logger.warning("Metrics pool not initialized, skipping save")
            return ""

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO model_execution_metrics (
                        task_id, agent_id, selected_model, provider,
                        alternatives_considered, capability_match_score, total_score,
                        latency_ms, prompt_tokens, completion_tokens, total_tokens,
                        estimated_cost, success, error, fallback_used, fallback_model,
                        created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
                    ) RETURNING id
                """,
                    metrics.task_id,
                    metrics.agent_id,
                    metrics.selected_model,
                    metrics.provider,
                    metrics.alternatives_considered,
                    metrics.capability_match_score,
                    metrics.total_score,
                    metrics.latency_ms,
                    metrics.prompt_tokens,
                    metrics.completion_tokens,
                    metrics.total_tokens,
                    metrics.estimated_cost,
                    metrics.success,
                    metrics.error,
                    metrics.fallback_used,
                    metrics.fallback_model,
                    metrics.created_at,
                )
                
                metrics_id = str(row["id"])
                logger.debug(f"Saved metrics {metrics_id} for task {metrics.task_id}")
                return metrics_id

        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            return ""

    async def get_model_stats(
        self,
        model_name: Optional[str] = None,
        days: int = 7,
    ) -> dict:
        """
        Get aggregated statistics for models.
        
        Args:
            model_name: Filter by specific model (optional)
            days: Number of days to look back
            
        Returns:
            Dictionary with aggregated stats
        """
        if not self.pool:
            return {}

        since = datetime.utcnow() - timedelta(days=days)
        
        try:
            async with self.pool.acquire() as conn:
                if model_name:
                    rows = await conn.fetch("""
                        SELECT 
                            selected_model,
                            COUNT(*) as total_calls,
                            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
                            AVG(latency_ms) as avg_latency_ms,
                            SUM(total_tokens) as total_tokens,
                            SUM(estimated_cost) as total_cost,
                            SUM(CASE WHEN fallback_used THEN 1 ELSE 0 END) as fallback_count
                        FROM model_execution_metrics
                        WHERE created_at > $1 AND selected_model = $2
                        GROUP BY selected_model
                    """, since, model_name)
                else:
                    rows = await conn.fetch("""
                        SELECT 
                            selected_model,
                            COUNT(*) as total_calls,
                            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
                            AVG(latency_ms) as avg_latency_ms,
                            SUM(total_tokens) as total_tokens,
                            SUM(estimated_cost) as total_cost,
                            SUM(CASE WHEN fallback_used THEN 1 ELSE 0 END) as fallback_count
                        FROM model_execution_metrics
                        WHERE created_at > $1
                        GROUP BY selected_model
                        ORDER BY total_calls DESC
                    """, since)

                return {
                    "period_days": days,
                    "models": [
                        {
                            "model": row["selected_model"],
                            "total_calls": row["total_calls"],
                            "success_rate": row["successful_calls"] / row["total_calls"] if row["total_calls"] > 0 else 0,
                            "avg_latency_ms": round(row["avg_latency_ms"] or 0),
                            "total_tokens": row["total_tokens"],
                            "total_cost": round(row["total_cost"] or 0, 4),
                            "fallback_rate": row["fallback_count"] / row["total_calls"] if row["total_calls"] > 0 else 0,
                        }
                        for row in rows
                    ],
                }

        except Exception as e:
            logger.error(f"Failed to get model stats: {e}")
            return {}

    async def get_recent_failures(self, limit: int = 10) -> List[dict]:
        """Get recent failed executions for debugging."""
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT task_id, agent_id, selected_model, provider, error, created_at
                    FROM model_execution_metrics
                    WHERE success = FALSE
                    ORDER BY created_at DESC
                    LIMIT $1
                """, limit)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent failures: {e}")
            return []


# Singleton instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get the metrics service singleton."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
