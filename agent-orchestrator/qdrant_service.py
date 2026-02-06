"""
Qdrant vector database client for semantic memory storage and retrieval.
"""
import logging
from typing import Optional
from uuid import uuid4
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
)

from config import get_settings
from embeddings import get_embeddings_client

logger = logging.getLogger(__name__)


class QdrantMemoryClient:
    """Client for storing and retrieving agent memories in Qdrant."""
    
    COLLECTION_NAME = "agent_memories"
    
    def __init__(self):
        settings = get_settings()
        self.client = AsyncQdrantClient(url=settings.qdrant_url)
        self.embeddings = get_embeddings_client()
        self.dimensions = settings.embedding_dimensions
        self._initialized = False
    
    async def initialize(self):
        """Initialize the Qdrant collection if it doesn't exist."""
        if self._initialized:
            return
        
        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.COLLECTION_NAME not in collection_names:
                await self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.dimensions,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.COLLECTION_NAME}")
            
            self._initialized = True
            logger.info("Qdrant client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise
    
    async def store_memory(
        self,
        agent_id: str,
        office_id: str,
        memory_key: str,
        memory_value: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Store a memory with its vector embedding.
        
        Args:
            agent_id: The agent this memory belongs to
            office_id: The office context
            memory_key: Short key/title for the memory
            memory_value: The full memory content
            memory_type: Type of memory (fact, preference, correction, insight)
            importance: Importance score 0.0-1.0
            metadata: Additional metadata
            
        Returns:
            The generated point ID
        """
        await self.initialize()
        
        # Generate embedding for the combined key and value
        text_to_embed = f"{memory_key}: {memory_value}"
        embedding = await self.embeddings.generate(text_to_embed)
        
        point_id = str(uuid4())
        
        payload = {
            "agent_id": agent_id,
            "office_id": office_id,
            "memory_key": memory_key,
            "memory_value": memory_value,
            "memory_type": memory_type,
            "importance": importance,
            "text": text_to_embed,
            **(metadata or {}),
        }
        
        await self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        
        logger.debug(f"Stored memory for agent {agent_id}: {memory_key}")
        return point_id
    
    async def search_memories(
        self,
        query: str,
        agent_id: str,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> list[dict]:
        """
        Search for semantically similar memories.
        
        Args:
            query: The search query
            agent_id: Filter to this agent's memories
            limit: Maximum number of results
            min_score: Minimum similarity score (0.0-1.0)
            
        Returns:
            List of memory dictionaries with scores
        """
        await self.initialize()
        
        # Generate embedding for the query
        query_embedding = await self.embeddings.generate(query)
        
        # Search with agent filter
        response = await self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_embedding,
            filter=Filter(
                must=[
                    FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=agent_id),
                    )
                ]
            ),
            limit=limit,
            score_threshold=min_score,
            params=SearchParams(
                hnsw_ef=128,  # Higher = more accurate, slower
                exact=False,
            ),
        )
        
        memories = []
        for result in response.points:
            memory = {
                "id": result.id,
                "score": result.score,
                "key": result.payload.get("memory_key", ""),
                "value": result.payload.get("memory_value", ""),
                "type": result.payload.get("memory_type", "fact"),
                "importance": result.payload.get("importance", 0.5),
            }
            memories.append(memory)
        
        logger.debug(f"Found {len(memories)} relevant memories for agent {agent_id}")
        return memories
    
    async def delete_memory(self, point_id: str):
        """Delete a memory by its point ID."""
        await self.initialize()
        await self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=[point_id],
        )
        logger.debug(f"Deleted memory: {point_id}")
    
    async def get_agent_memory_count(self, agent_id: str) -> int:
        """Get the total number of memories for an agent."""
        await self.initialize()
        
        result = await self.client.count(
            collection_name=self.COLLECTION_NAME,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=agent_id),
                    )
                ]
            ),
        )
        return result.count


# Singleton instance
_qdrant_client: Optional[QdrantMemoryClient] = None


async def get_qdrant_client() -> QdrantMemoryClient:
    """Get the Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantMemoryClient()
        await _qdrant_client.initialize()
    return _qdrant_client
