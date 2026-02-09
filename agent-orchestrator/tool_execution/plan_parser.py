import re
import json
import logging
from typing import Optional, Dict, Any, List
from .types import ActionPlan

logger = logging.getLogger(__name__)

class ActionPlanParser:
    """Parses LLM text responses into structured ActionPlans."""

    @staticmethod
    def extract_json_block(text: str) -> Optional[str]:
        """Extract JSON block from text, handling markdown fences."""
        # Try finding markdown code block
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try finding raw JSON object if enclosed in braces
        # This is a simple heuristic and might catch false positives if text contains braces
        # A improved regex could look for the outermost braces
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match:
            return json_match.group(1)

        return None

    @staticmethod
    def parse(response_text: str) -> Optional[ActionPlan]:
        """
        Parse LLM response text into an ActionPlan.
        Returns None if no valid plan is found.
        """
        json_str = ActionPlanParser.extract_json_block(response_text)
        
        if not json_str:
            # If no JSON block found, maybe the whole text is JSON?
            # Or strict JSON extraction failed.
            # Try parsing the whole text as a fallback
            try:
                data = json.loads(response_text)
                return ActionPlan(**data)
            except json.JSONDecodeError:
                return None

        try:
            data = json.loads(json_str)
            return ActionPlan(**data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode extracted JSON block: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to validate ActionPlan: {e}")
            return None
