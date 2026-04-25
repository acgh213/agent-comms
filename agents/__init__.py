"""Agent definitions and registry."""

from agents.coder import CODER
from agents.devops import DEVOPS
from agents.editor import EDITOR
from agents.planner import PLANNER
from agents.qa import QA
from agents.researcher import RESEARCHER
from agents.vesper import VESPER
from agents.writer import WRITER
from agents.registry import AgentRegistry, default_registry

__all__ = [
    "VESPER",
    "CODER",
    "EDITOR",
    "PLANNER",
    "RESEARCHER",
    "QA",
    "DEVOPS",
    "WRITER",
    "AgentRegistry",
    "default_registry",
]
