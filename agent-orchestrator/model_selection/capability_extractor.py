"""Capability Extractor - Extracts required capabilities from tasks and context."""

import logging
import re
from typing import Dict, Optional
from pathlib import Path
import yaml

from .types import TaskCapabilityProfile, CostLevel

logger = logging.getLogger(__name__)


# Keyword patterns for capability detection
CAPABILITY_PATTERNS = {
    "coding": [
        r"\b(code|coding|program|function|class|debug|implement|refactor)\b",
        r"\b(python|javascript|java|go|rust|typescript|sql|api)\b",
        r"\b(bug|error|fix|compile|syntax|algorithm)\b",
    ],
    "reasoning": [
        r"\b(analyze|think|reason|explain|understand|evaluate)\b",
        r"\b(why|how|compare|contrast|assess|deduce)\b",
        r"\b(logic|inference|conclusion|hypothesis)\b",
    ],
    "summarization": [
        r"\b(summarize|summary|brief|overview|tldr|recap)\b",
        r"\b(condense|shorten|highlight|key.?points)\b",
    ],
    "planning": [
        r"\b(plan|schedule|organize|coordinate|roadmap|timeline)\b",
        r"\b(project|milestone|task|deadline|priority)\b",
        r"\b(strategy|approach|steps|phases)\b",
    ],
    "long_context": [
        r"\b(document|report|article|paper|book|chapter)\b",
        r"\b(entire|full|complete|whole|all.?of)\b",
        r"\b(review|read|analyze).+(long|large|extensive)\b",
    ],
    "structured_output": [
        r"\b(json|yaml|xml|csv|table|list|format)\b",
        r"\b(structured|formatted|organized|template)\b",
        r"\b(schema|fields|columns|rows)\b",
    ],
    "multimodal": [
        r"\b(image|photo|picture|diagram|chart|graph)\b",
        r"\b(visual|see|look|show|display)\b",
    ],
    "web_search": [
        r"\b(search|find|lookup|latest|current|recent)\b",
        r"\b(news|today|now|updated)\b",
    ],
}

# Agent role to capability mapping
ROLE_CAPABILITIES = {
    "Engineer": {
        "required": {"coding": 0.9, "reasoning": 0.7},
        "preferred": {"structured_output": 0.5},
        "min_score": 7,
    },
    "Analyst": {
        "required": {"reasoning": 0.8, "summarization": 0.7},
        "preferred": {"long_context": 0.5},
        "min_score": 6,
    },
    "Writer": {
        "required": {"summarization": 0.8},
        "preferred": {"long_context": 0.4},
        "min_score": 5,
    },
    "Planner": {
        "required": {"planning": 0.8, "reasoning": 0.6},
        "preferred": {"structured_output": 0.5},
        "min_score": 6,
    },
}


class CapabilityExtractor:
    """Extracts required capabilities from user input, agent role, and context."""

    def __init__(self, policies_path: Optional[str] = None):
        self.policies_path = policies_path or self._default_policies_path()
        self._role_capabilities = ROLE_CAPABILITIES.copy()
        self._loaded = False

    def _default_policies_path(self) -> str:
        """Get default policies path relative to this file."""
        return str(Path(__file__).parent.parent / "config" / "policies.yaml")

    async def load(self) -> None:
        """Load role capability mappings from policies config."""
        if self._loaded:
            return

        try:
            with open(self.policies_path, "r") as f:
                config = yaml.safe_load(f)
            
            # Override defaults with config values
            role_config = config.get("role_capabilities", {})
            for role, caps in role_config.items():
                self._role_capabilities[role] = {
                    "required": {k: 0.8 for k in caps.get("required", [])},
                    "preferred": {k: 0.5 for k in caps.get("preferred", [])},
                    "min_score": caps.get("min_score", 5),
                }
            self._loaded = True
            logger.debug(f"Loaded role capabilities for {len(self._role_capabilities)} roles")

        except Exception as e:
            logger.warning(f"Could not load policies config: {e}, using defaults")
            self._loaded = True

    def extract(
        self,
        user_input: str,
        agent_role: Optional[str] = None,
        context_length: int = 0,
    ) -> TaskCapabilityProfile:
        """
        Extract capability requirements from task context.
        
        Args:
            user_input: The user's message/task
            agent_role: The agent's role (e.g., "Engineer", "Analyst")
            context_length: Approximate context length needed
            
        Returns:
            TaskCapabilityProfile with required capabilities
        """
        # Start with capabilities from text analysis
        capabilities = self._extract_from_text(user_input)
        
        # Merge with role-based requirements
        if agent_role and agent_role in self._role_capabilities:
            role_caps = self._role_capabilities[agent_role]
            for cap, weight in role_caps.get("required", {}).items():
                # Take the higher weight
                capabilities[cap] = max(capabilities.get(cap, 0), weight)
            for cap, weight in role_caps.get("preferred", {}).items():
                if cap not in capabilities:
                    capabilities[cap] = weight
        
        # Determine if long context is needed
        requires_long_context = context_length > 8000 or capabilities.get("long_context", 0) > 0.5
        
        # Check for sensitive content
        requires_local = self._check_sensitive_content(user_input)
        
        # Get minimum capability score from role
        min_score = 5
        if agent_role and agent_role in self._role_capabilities:
            min_score = self._role_capabilities[agent_role].get("min_score", 5)
        
        return TaskCapabilityProfile(
            required_capabilities=capabilities,
            min_capability_score=min_score,
            max_cost_level=CostLevel.HIGH,
            requires_local=requires_local,
            context_length_needed=max(4000, context_length),
            agent_role=agent_role,
        )

    def _extract_from_text(self, text: str) -> Dict[str, float]:
        """Extract capabilities from text using pattern matching."""
        text_lower = text.lower()
        capabilities: Dict[str, float] = {}
        
        for capability, patterns in CAPABILITY_PATTERNS.items():
            match_count = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                match_count += len(matches)
            
            if match_count > 0:
                # Scale weight based on match frequency (max 1.0)
                weight = min(1.0, 0.3 + (match_count * 0.2))
                capabilities[capability] = weight
        
        return capabilities

    def _check_sensitive_content(self, text: str) -> bool:
        """Check if content contains sensitive patterns requiring local processing."""
        sensitive_patterns = [
            r"\b(confidential|secret|private|password|credential)\b",
            r"\b(internal|proprietary|trade.?secret)\b",
            r"\b(api.?key|access.?token|bearer)\b",
        ]
        
        text_lower = text.lower()
        for pattern in sensitive_patterns:
            if re.search(pattern, text_lower):
                logger.info("Sensitive content detected, requiring local model")
                return True
        
        return False


# Singleton instance
_extractor: Optional[CapabilityExtractor] = None


def get_capability_extractor() -> CapabilityExtractor:
    """Get the capability extractor singleton."""
    global _extractor
    if _extractor is None:
        _extractor = CapabilityExtractor()
    return _extractor
