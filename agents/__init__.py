"""Agent definitions and registry."""

from agents.vesper import VESPER
from agents.coder import CODER
from agents.editor import EDITOR
from agents.planner import PLANNER
from agents.registry import AgentRegistry, default_registry

__all__ = [
    "VESPER",
    "CODER",
    "EDITOR",
    "PLANNER",
    "AgentRegistry",
    "default_registry",
]
