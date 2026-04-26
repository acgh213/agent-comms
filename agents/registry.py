"""Agent registry — holds and manages all agent definitions."""

import os
import re
from pathlib import Path

import yaml

from agents.base import AgentDef
from agents.coder import CODER
from agents.devops import DEVOPS
from agents.editor import EDITOR
from agents.planner import PLANNER
from agents.qa import QA
from agents.researcher import RESEARCHER
from agents.vesper import VESPER
from agents.writer import WRITER

# ---------------------------------------------------------------------------
# Profile → role mapping
# ---------------------------------------------------------------------------
PROFILE_ROLES = {
    "vesper": "creative",
    "coder": "implementation",
    "editor": "quality",
    "planner": "architecture",
    "researcher": "research",
}

# ---------------------------------------------------------------------------
# Profile → avatar color
# ---------------------------------------------------------------------------
PROFILE_COLORS = {
    "vesper": "#FFD700",       # gold
    "coder": "#E6E6FA",        # lavender
    "editor": "#FF007F",       # rose
    "planner": "#008080",      # teal
    "researcher": "#7cacef",   # blue
}

HERMES_PROFILES_DIR = os.path.expanduser("~/.hermes/profiles")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_soul_personality(soul_path):
    """Extract the first paragraph after the # heading from a SOUL.md file.

    Returns the personality text, or empty string on failure.
    """
    try:
        text = Path(soul_path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""

    # Find the first `# ProfileName` heading, then grab the first non-blank
    # paragraph that follows (skipping over empty lines after the heading).
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("##"):
            # Skip blank lines that may appear right after the heading
            para_lines = []
            scanning = False
            for pline in lines[i + 1 :]:
                stripped = pline.strip()
                if not scanning:
                    if not stripped:
                        continue  # skip leading blank lines
                    scanning = True
                if not stripped:
                    break  # blank line ends the paragraph
                para_lines.append(stripped)
            if para_lines:
                return " ".join(para_lines)
    return ""


def _parse_config_model(config_path):
    """Extract the model name from a Hermes config.yaml.

    Returns the model string (e.g. ``"xiaomi/mimo-v2.5"``) or ``None``.
    """
    try:
        data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    model_section = data.get("model")
    if isinstance(model_section, dict):
        return model_section.get("default")
    return None


# ---------------------------------------------------------------------------
# Profile discovery
# ---------------------------------------------------------------------------

def discover_profiles():
    """Scan ``~/.hermes/profiles/`` and yield ``(profile_id, soul_path, config_path)``
    tuples for every profile directory that contains a ``SOUL.md``.
    """
    profiles_dir = Path(HERMES_PROFILES_DIR)
    if not profiles_dir.is_dir():
        return

    for entry in sorted(profiles_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        soul_path = entry / "SOUL.md"
        config_path = entry / "config.yaml"
        if soul_path.is_file():
            yield entry.name, soul_path, config_path


# ---------------------------------------------------------------------------
# DB sync
# ---------------------------------------------------------------------------

def sync_from_profiles(db=None):
    """Read Hermes profiles and upsert Agent records in the database.

    Parameters
    ----------
    db : SQLAlchemy instance, optional
        The Flask-SQLAlchemy ``db`` object.  If omitted, attempts to import
        from ``app`` — will work inside a Flask application context.

    Returns
    -------
    list[Agent]
        The list of Agent records that were created or updated.
    """
    if db is None:
        from app import db

    agent_records = []

    for profile_id, soul_path, config_path in discover_profiles():
        personality = _parse_soul_personality(soul_path)
        model = _parse_config_model(config_path)
        role = PROFILE_ROLES.get(profile_id, "assistant")
        color = PROFILE_COLORS.get(profile_id, "#888888")
        name = profile_id.capitalize()

        # Look up an existing agent by name, or create a new one.
        from models import Agent

        agent = db.session.query(Agent).filter_by(name=name).first()
        if agent is None:
            agent = Agent(
                name=name,
                role=role,
                personality=personality,
                capabilities=list(_extract_capabilities(profile_id)),
                avatar_color=color,
                status="offline",
            )
            db.session.add(agent)
        else:
            # Update fields from profile in case they changed.
            agent.role = role
            agent.personality = personality or agent.personality
            agent.avatar_color = color
            if not agent.capabilities:
                agent.capabilities = list(_extract_capabilities(profile_id))

        # Sync preferred_model from AgentDef if available
        agent_def = default_registry.get(profile_id)
        if agent_def and agent_def.preferred_model:
            agent.preferred_model = agent_def.preferred_model

        agent_records.append(agent)

    db.session.commit()
    return agent_records


def _extract_capabilities(profile_id):
    """Return a list of capabilities for a given profile."""
    caps_map = {
        "vesper": ["creative_direction", "narrative_design", "world_building", "content_generation"],
        "coder": ["code_generation", "debugging", "refactoring", "test_writing"],
        "editor": ["proofreading", "style_enforcement", "fact_checking", "formatting"],
        "planner": ["system_design", "task_decomposition", "dependency_analysis", "risk_assessment"],
        "researcher": ["research", "analysis", "synthesis", "bibliography", "fact-checking"],
    }
    return caps_map.get(profile_id, [])


def sync_agents(db=None, registry=None):
    """High-level entry-point: sync Hermes profiles into the DB, then populate
    an AgentRegistry (defaulting to the module-level ``default_registry``).

    Returns the list of created/updated Agent model instances.
    """
    agents = sync_from_profiles(db=db)

    if registry is None:
        from agents.registry import default_registry as registry

    # Rebuild the in-memory registry from the synced DB records.
    registry.clear()
    registry.register(VESPER)
    registry.register(CODER)
    registry.register(EDITOR)
    registry.register(PLANNER)
    registry.register(RESEARCHER)
    registry.register(QA)
    registry.register(DEVOPS)
    registry.register(WRITER)

    # Also ensure code-defined agents without profiles exist in the DB
    if db is None:
        from app import db

    from models import Agent
    agent_names_in_db = {a.name for a in agents}

    for agent_def in registry.list():
        if agent_def.name not in agent_names_in_db:
            role_map = {
                "vesper": "creative",
                "coder": "implementation",
                "editor": "quality",
                "planner": "architecture",
                "researcher": "research",
                "qa": "quality-assurance",
                "devops": "infrastructure",
                "writer": "content",
            }
            # Check DB directly in case name exists but wasn't in initial query
            existing = db.session.query(Agent).filter_by(name=agent_def.name).first()
            if existing:
                # Update model if changed
                if agent_def.preferred_model:
                    existing.preferred_model = agent_def.preferred_model
                agent_names_in_db.add(agent_def.name)
                continue

            agent = Agent(
                name=agent_def.name,
                role=role_map.get(agent_def.id, agent_def.role),
                personality=agent_def.personality,
                capabilities=agent_def.capabilities,
                avatar_color=agent_def.avatar_color,
                preferred_model=agent_def.preferred_model,
                status="offline",
            )
            db.session.add(agent)
            agents.append(agent)

    db.session.commit()
    return agents


# ---------------------------------------------------------------------------
# AgentRegistry
# ---------------------------------------------------------------------------

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
