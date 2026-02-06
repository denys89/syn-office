"""
Memory extraction module for learning from conversations.
Uses LLM to extract key facts, preferences, and insights from user messages.
"""
import logging
from typing import Optional
from openai import AsyncOpenAI

from config import get_settings

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """Extracts learnable information from conversations using LLM."""
    
    EXTRACTION_PROMPT = """You are a memory extraction assistant. Analyze the conversation and extract important information that should be remembered for future interactions.

Extract the following types of information if present:
1. **Facts** - Specific facts the user mentioned (e.g., "User's company is Acme Corp")
2. **Preferences** - User preferences about communication or work style (e.g., "User prefers concise responses")
3. **Corrections** - Things the user corrected or clarified (e.g., "User corrected: use Python 3.10+, not 3.8")
4. **Insights** - Important context about the user's situation or needs

For each extracted memory, provide:
- type: fact | preference | correction | insight
- key: A short, descriptive key (3-8 words)
- value: The full detail of the memory
- importance: 0.0-1.0 score (1.0 = very important)

Respond ONLY with valid JSON in this format:
{
    "memories": [
        {
            "type": "preference",
            "key": "Prefers detailed explanations",
            "value": "User explicitly stated they prefer detailed technical explanations with code examples",
            "importance": 0.8
        }
    ]
}

If there's nothing worth remembering, return: {"memories": []}"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4-turbo-preview"  # Use capable model for extraction
    
    async def extract_memories(
        self, 
        user_message: str, 
        agent_response: str,
        existing_memories: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Extract learnable memories from a conversation exchange.
        
        Args:
            user_message: The user's message
            agent_response: The agent's response
            existing_memories: Current memories to avoid duplicates
            
        Returns:
            List of extracted memory dictionaries
        """
        # Build context
        context = f"""USER MESSAGE:
{user_message}

AGENT RESPONSE:
{agent_response}"""
        
        if existing_memories:
            context += f"""

EXISTING MEMORIES (avoid duplicates):
{chr(10).join(f'- {m}' for m in existing_memories[:10])}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.EXTRACTION_PROMPT},
                    {"role": "user", "content": context},
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.3,  # Lower temperature for consistent extraction
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            memories = result.get("memories", [])
            
            # Validate and filter memories
            valid_memories = []
            for mem in memories:
                if all(k in mem for k in ["type", "key", "value", "importance"]):
                    # Ensure importance is in valid range
                    mem["importance"] = max(0.0, min(1.0, float(mem["importance"])))
                    valid_memories.append(mem)
            
            logger.debug(f"Extracted {len(valid_memories)} memories from conversation")
            return valid_memories
            
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []
    
    async def should_extract(self, message: str) -> bool:
        """
        Determine if a message is worth analyzing for memory extraction.
        Quick heuristic check to avoid unnecessary API calls.
        """
        # Skip very short messages
        if len(message) < 20:
            return False
        
        # Keywords that often indicate learnable content
        learning_keywords = [
            "prefer", "like", "want", "always", "never", "remember",
            "i am", "i'm", "my", "our", "we use", "we have",
            "don't", "please", "actually", "correct", "instead",
            "company", "team", "project", "work", "job",
        ]
        
        message_lower = message.lower()
        return any(kw in message_lower for kw in learning_keywords)


# Singleton instance
_memory_extractor: Optional[MemoryExtractor] = None


def get_memory_extractor() -> MemoryExtractor:
    """Get the memory extractor singleton."""
    global _memory_extractor
    if _memory_extractor is None:
        _memory_extractor = MemoryExtractor()
    return _memory_extractor
