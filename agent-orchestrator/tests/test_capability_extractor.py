"""Tests for Capability Extractor."""

import pytest
from model_selection.capability_extractor import CapabilityExtractor
from model_selection.types import CostLevel


class TestCapabilityExtractor:
    """Test suite for CapabilityExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a fresh extractor instance."""
        ext = CapabilityExtractor()
        ext._loaded = True  # Skip loading config
        return ext

    def test_extract_coding_capability(self, extractor):
        """Test detection of coding-related tasks."""
        profile = extractor.extract(
            user_input="Write a Python function to sort a list",
            agent_role="Engineer",
        )
        
        assert "coding" in profile.required_capabilities
        assert profile.required_capabilities["coding"] >= 0.5

    def test_extract_reasoning_capability(self, extractor):
        """Test detection of reasoning tasks."""
        profile = extractor.extract(
            user_input="Analyze why our sales dropped and explain the reasons",
            agent_role="Analyst",
        )
        
        assert "reasoning" in profile.required_capabilities

    def test_extract_summarization_capability(self, extractor):
        """Test detection of summarization tasks."""
        profile = extractor.extract(
            user_input="Summarize this document and give me the key points",
            agent_role="Writer",
        )
        
        assert "summarization" in profile.required_capabilities

    def test_extract_planning_capability(self, extractor):
        """Test detection of planning tasks."""
        profile = extractor.extract(
            user_input="Create a project plan with milestones and deadlines",
            agent_role="Planner",
        )
        
        assert "planning" in profile.required_capabilities

    def test_agent_role_affects_requirements(self, extractor):
        """Test that agent role influences capability requirements."""
        same_input = "Help me with this task"
        
        engineer_profile = extractor.extract(same_input, agent_role="Engineer")
        writer_profile = extractor.extract(same_input, agent_role="Writer")
        
        assert engineer_profile.min_capability_score >= writer_profile.min_capability_score

    def test_sensitive_content_detection(self, extractor):
        """Test that sensitive content triggers local model requirement."""
        profile = extractor.extract(
            user_input="Here is my password: supersecret123",
        )
        
        assert profile.requires_local is True

    def test_sensitive_api_key_detection(self, extractor):
        """Test detection of API key patterns."""
        profile = extractor.extract(
            user_input="My API key is sk-1234567890abcdef",
        )
        
        assert profile.requires_local is True

    def test_non_sensitive_content(self, extractor):
        """Test that normal content doesn't require local model."""
        profile = extractor.extract(
            user_input="Write a poem about the ocean",
        )
        
        assert profile.requires_local is False

    def test_context_length_estimation(self, extractor):
        """Test that context length is properly set."""
        profile = extractor.extract(
            user_input="Short task",
            context_length=16000,
        )
        
        assert profile.context_length_needed >= 16000

    def test_structured_output_detection(self, extractor):
        """Test detection of structured output requirements."""
        profile = extractor.extract(
            user_input="Return the data as JSON with these fields: name, age, email",
        )
        
        assert "structured_output" in profile.required_capabilities
