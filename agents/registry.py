"""Agent registry — holds and manages all agent definitions."""

from agents.base import AgentDef
from agents.coder import CODER
from agents.devops import DEVOPS
from agents.editor import EDITOR
from agents.planner import PLANNER
from agents.qa import QA
from agents.researcher import RESEARCHER
from agents.vesper import VESPER
from agents.writer import WRITER


class AgentRegistry:
    """Registry of all known agent definitions."""

    def __init__(self):
        self._agents = {}

    def register(self, agent_def):
        """Register an AgentDef. Overwrites if id already exists."""
        self._agents[agent_def.id] = agent_def

    def get(self, agent_id):
        """Get an AgentDef by id, or None."""
        return self._agents.get(agent_id)

    def list(self):
        """Return all registered AgentDefs."""
        return list(self._agents.values())

    def get_by_role(self, role):
        """Return all AgentDefs with the given role."""
        return [a for a in self._agents.values() if a.role == role]

    def clear(self):
        """Remove all registered agents."""
        self._agents.clear()

    def __len__(self):
        return len(self._agents)


# Default registry pre-populated with all eight standard agents
default_registry = AgentRegistry()
default_registry.register(VESPER)
default_registry.register(CODER)
default_registry.register(EDITOR)
default_registry.register(PLANNER)
default_registry.register(RESEARCHER)
default_registry.register(QA)
default_registry.register(DEVOPS)
default_registry.register(WRITER)
