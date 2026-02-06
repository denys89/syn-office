from openai import AsyncOpenAI
from typing import Optional
import logging

from config import get_settings
from models import Message, AgentContext

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with OpenAI-compatible LLMs."""
    
    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def generate(
        self,
        context: AgentContext,
        user_input: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> tuple[str, dict]:
        """
        Generate a response from the LLM.
        
        Returns:
            Tuple of (response_text, token_usage_dict)
        """
        messages = self._build_messages(context, user_input)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            output = response.choices[0].message.content
            token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            return output, token_usage
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise
    
    def _build_messages(self, context: AgentContext, user_input: str) -> list[dict]:
        """Build the messages array for the LLM."""
        messages = []
        
        # System prompt with agent identity
        system_content = self._build_system_prompt(context)
        messages.append({"role": "system", "content": system_content})
        
        # Conversation history
        for msg in context.conversation_history[-10:]:  # Last 10 messages for context
            messages.append({
                "role": "user" if msg.get("sender_type") == "user" else "assistant",
                "content": msg.get("content", ""),
            })
        
        # Current user input
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _build_system_prompt(self, context: AgentContext) -> str:
        """Build the full system prompt with context."""
        prompt_parts = [
            context.system_prompt,
            "",
            "IMPORTANT GUIDELINES:",
            "- You are part of Synoffice, an AI-native digital office.",
            "- Respond professionally and helpfully.",
            "- Stay within your role and expertise.",
            "- If asked about something outside your expertise, acknowledge it and suggest the appropriate agent.",
            "",
        ]
        
        # Add memories if available
        if context.memories:
            prompt_parts.extend([
                "RELEVANT MEMORIES:",
                *[f"- {memory}" for memory in context.memories],
                "",
            ])
        
        return "\n".join(prompt_parts)


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
