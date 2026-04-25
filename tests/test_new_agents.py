"""Tests for the four new specialist agent definitions."""


class TestResearcher:
    """Tests for the Researcher agent."""

    def test_researcher_agent_definition(self):
        """Researcher has correct identity and capabilities."""
        from agents import RESEARCHER

        assert RESEARCHER.id == "researcher"
        assert RESEARCHER.name == "Researcher"
        assert RESEARCHER.role == "research"
        assert "research" in RESEARCHER.capabilities
        assert "analysis" in RESEARCHER.capabilities
        assert "bibliography" in RESEARCHER.capabilities
        assert RESEARCHER.avatar_color == "#7cacef"

    def test_researcher_personality(self):
        """Researcher has a curiosity-driven personality."""
        from agents import RESEARCHER

        assert "Curious" in RESEARCHER.personality
        assert "methodical" in RESEARCHER.personality


class TestQA:
    """Tests for the QA agent."""

    def test_qa_agent_definition(self):
        """QA has correct identity and capabilities."""
        from agents import QA

        assert QA.id == "qa"
        assert QA.name == "QA"
        assert QA.role == "quality-assurance"
        assert "testing" in QA.capabilities
        assert "bug-finding" in QA.capabilities
        assert "regression" in QA.capabilities
        assert QA.avatar_color == "#ef7c7c"

    def test_qa_personality(self):
        """QA has a meticulous, skeptical personality."""
        from agents import QA

        assert "Meticulous" in QA.personality
        assert "edge cases" in QA.personality


class TestDevOps:
    """Tests for the DevOps agent."""

    def test_devops_agent_definition(self):
        """DevOps has correct identity and capabilities."""
        from agents import DEVOPS

        assert DEVOPS.id == "devops"
        assert DEVOPS.name == "DevOps"
        assert DEVOPS.role == "infrastructure"
        assert "deployment" in DEVOPS.capabilities
        assert "monitoring" in DEVOPS.capabilities
        assert "security" in DEVOPS.capabilities
        assert DEVOPS.avatar_color == "#7cefce"

    def test_devops_personality(self):
        """DevOps has a pragmatic, security-minded personality."""
        from agents import DEVOPS

        assert "Pragmatic" in DEVOPS.personality
        assert "security-minded" in DEVOPS.personality


class TestWriter:
    """Tests for the Writer agent."""

    def test_writer_agent_definition(self):
        """Writer has correct identity and capabilities."""
        from agents import WRITER

        assert WRITER.id == "writer"
        assert WRITER.name == "Writer"
        assert WRITER.role == "content"
        assert "writing" in WRITER.capabilities
        assert "editing" in WRITER.capabilities
        assert "documentation" in WRITER.capabilities
        assert WRITER.avatar_color == "#efcf7c"

    def test_writer_personality(self):
        """Writer has an eloquent, voice-aware personality."""
        from agents import WRITER

        assert "Eloquent" in WRITER.personality
        assert "voice-aware" in WRITER.personality
