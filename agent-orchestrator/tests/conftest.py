"""Pytest configuration and fixtures for model selection tests."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_user_inputs():
    """Sample user inputs for testing."""
    return {
        "coding": "Write a Python function to implement a binary search algorithm",
        "reasoning": "Analyze why our quarterly revenue dropped by 15% and explain the key factors",
        "summarization": "Summarize this 10-page report and give me the key takeaways",
        "planning": "Create a project plan with milestones for our Q2 product launch",
        "sensitive": "Here is my API key: sk-1234567890 please keep it secret",
        "simple": "Hello, how are you today?",
    }


@pytest.fixture
def sample_agent_roles():
    """Sample agent roles for testing."""
    return ["Engineer", "Analyst", "Writer", "Planner"]
