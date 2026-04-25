"""Tests for agent registry system."""


class TestAgentDef:
    """Test the AgentDef base class."""

    def test_create_agent_def(self):
        """Create an AgentDef with all fields."""
        from agents.base import AgentDef

        agent = AgentDef(
            id="test_bot",
            name="TestBot",
            role="tester",
            personality="thorough and meticulous",
            capabilities=["testing", "reporting"],
            avatar_color="#FF5733",
        )

        assert agent.id == "test_bot"
        assert agent.name == "TestBot"
        assert agent.role == "tester"
        assert agent.personality == "thorough and meticulous"
        assert agent.capabilities == ["testing", "reporting"]
        assert agent.avatar_color == "#FF5733"

    def test_agent_def_defaults(self):
        """AgentDef provides sensible defaults."""
        from agents.base import AgentDef

        agent = AgentDef(id="minimal", name="MinimalBot", role="helper")

        assert agent.personality == ""
        assert agent.capabilities == []
        assert agent.avatar_color == "#888888"

    def test_agent_def_to_dict(self):
        """AgentDef can serialize to dict."""
        from agents.base import AgentDef

        agent = AgentDef(
            id="dict_bot",
            name="DictBot",
            role="serializer",
            personality="friendly",
            capabilities=["talk"],
            avatar_color="#000000",
        )

        d = agent.to_dict()
        assert d["id"] == "dict_bot"
        assert d["name"] == "DictBot"
        assert d["role"] == "serializer"
        assert d["personality"] == "friendly"
        assert d["capabilities"] == ["talk"]
        assert d["avatar_color"] == "#000000"

    def test_agent_def_equality(self):
        """AgentDef equality is based on id."""
        from agents.base import AgentDef

        a1 = AgentDef(id="same", name="One", role="a")
        a2 = AgentDef(id="same", name="Two", role="b")

        assert a1 == a2
        assert hash(a1) == hash(a2)


class TestAgentRegistry:
    """Test the AgentRegistry."""

    def test_empty_registry(self):
        """New registry has no agents."""
        from agents.registry import AgentRegistry

        registry = AgentRegistry()
        assert registry.list() == []
        assert registry.get("nonexistent") is None

    def test_register_and_get(self):
        """Register an agent and retrieve it by id."""
        from agents.base import AgentDef
        from agents.registry import AgentRegistry

        registry = AgentRegistry()
        agent = AgentDef(id="test", name="TestAgent", role="tester")

        registry.register(agent)
        assert registry.get("test") is agent

    def test_register_duplicate_overwrites(self):
        """Registering same id overwrites previous."""
        from agents.base import AgentDef
        from agents.registry import AgentRegistry

        registry = AgentRegistry()
        a1 = AgentDef(id="dup", name="First", role="a")
        a2 = AgentDef(id="dup", name="Second", role="b")

        registry.register(a1)
        registry.register(a2)
        assert registry.get("dup").name == "Second"

    def test_list_agents(self):
        """List returns all registered agents."""
        from agents.base import AgentDef
        from agents.registry import AgentRegistry

        registry = AgentRegistry()
        a1 = AgentDef(id="one", name="One", role="a")
        a2 = AgentDef(id="two", name="Two", role="b")

        registry.register(a1)
        registry.register(a2)

        agents = registry.list()
        assert len(agents) == 2
        assert a1 in agents
        assert a2 in agents

    def test_get_by_role(self):
        """Filter agents by role."""
        from agents.base import AgentDef
        from agents.registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(AgentDef(id="a1", name="Alpha", role="worker"))
        registry.register(AgentDef(id="a2", name="Beta", role="worker"))
        registry.register(AgentDef(id="a3", name="Gamma", role="supervisor"))

        workers = registry.get_by_role("worker")
        assert len(workers) == 2
        assert all(a.role == "worker" for a in workers)

        supervisors = registry.get_by_role("supervisor")
        assert len(supervisors) == 1

    def test_get_by_role_none(self):
        """get_by_role returns empty list when no match."""
        from agents.base import AgentDef
        from agents.registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(AgentDef(id="a1", name="A", role="worker"))

        assert registry.get_by_role("manager") == []

    def test_register_many_and_clear(self):
        """Register multiple and clear all."""
        from agents.base import AgentDef
        from agents.registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(AgentDef(id="a", name="A", role="a"))
        registry.register(AgentDef(id="b", name="B", role="b"))

        assert len(registry.list()) == 2
        registry.clear()
        assert registry.list() == []


class TestPredefinedAgents:
    """Test the predefined agent definitions."""

    def test_vesper_agent(self):
        """VESPER is creative with gold color."""
        from agents import VESPER

        assert VESPER.id == "vesper"
        assert VESPER.role == "creative"
        assert VESPER.avatar_color == "#FFD700"

    def test_coder_agent(self):
        """CODER is implementation with lavender color."""
        from agents import CODER

        assert CODER.id == "coder"
        assert CODER.role == "implementation"
        assert CODER.avatar_color == "#E6E6FA"

    def test_editor_agent(self):
        """EDITOR is quality with rose color."""
        from agents import EDITOR

        assert EDITOR.id == "editor"
        assert EDITOR.role == "quality"
        assert EDITOR.avatar_color == "#FF007F"

    def test_planner_agent(self):
        """PLANNER is architecture with teal color."""
        from agents import PLANNER

        assert PLANNER.id == "planner"
        assert PLANNER.role == "architecture"
        assert PLANNER.avatar_color == "#008080"

    def test_default_registry_has_all(self):
        """Default registry contains all eight agents."""
        from agents.registry import default_registry

        agents = default_registry.list()
        ids = {a.id for a in agents}
        assert ids == {
            "vesper",
            "coder",
            "editor",
            "planner",
            "researcher",
            "qa",
            "devops",
            "writer",
        }
        assert len(agents) == 8
