"""Tests for Hermes profile sync into the Agent registry."""

import os
import tempfile
import textwrap
from pathlib import Path

import pytest
import yaml

from agents.registry import (
    PROFILE_COLORS,
    PROFILE_ROLES,
    _parse_config_model,
    _parse_soul_personality,
    discover_profiles,
)


# ===========================================================================
# Parsing helpers
# ===========================================================================

class TestParseSoulPersonality:
    """_parse_soul_personality extracts the first paragraph after # heading."""

    def test_standard_soul(self):
        """Standard SOUL.md with # heading followed by paragraph."""
        text = textwrap.dedent("""\
            # Coder Agent

            You are a methodical, thorough, pragmatic coding agent. You write clean, maintainable code and follow TDD religiously.

            ## Style
            - Write code that speaks for itself
        """)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(text)
            path = f.name
        try:
            result = _parse_soul_personality(path)
            assert (
                result
                == "You are a methodical, thorough, pragmatic coding agent. You write clean, maintainable code and follow TDD religiously."
            )
        finally:
            os.unlink(path)

    def test_no_heading(self):
        """No '#' heading → empty string."""
        text = """Just some text without a heading."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(text)
            path = f.name
        try:
            assert _parse_soul_personality(path) == ""
        finally:
            os.unlink(path)

    def test_empty_paragraph(self):
        """Heading followed immediately by blank lines → empty string."""
        text = """# Coder Agent

"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(text)
            path = f.name
        try:
            assert _parse_soul_personality(path) == ""
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        """Missing file → empty string."""
        assert _parse_soul_personality("/nonexistent/SOUL.md") == ""

    def test_multiline_paragraph(self):
        """Paragraph spanning multiple lines is joined."""
        text = textwrap.dedent("""\
            # Editor Agent

            You are a sharp,
            detail-oriented,
            constructive editing agent.

            ## Style
            - Be direct
        """)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(text)
            path = f.name
        try:
            result = _parse_soul_personality(path)
            assert "sharp" in result
            assert "detail-oriented" in result
            assert "constructive editing agent" in result
        finally:
            os.unlink(path)


class TestParseConfigModel:
    """_parse_config_model extracts model.default from config.yaml."""

    def test_standard_config(self):
        """Standard config with model.default."""
        data = {"model": {"default": "xiaomi/mimo-v2.5"}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = f.name
        try:
            assert _parse_config_model(path) == "xiaomi/mimo-v2.5"
        finally:
            os.unlink(path)

    def test_no_model_section(self):
        """Config without model section → None."""
        data = {"terminal": {"backend": "local"}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = f.name
        try:
            assert _parse_config_model(path) is None
        finally:
            os.unlink(path)

    def test_empty_model(self):
        """Config with empty model section → None."""
        data = {"model": {}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            path = f.name
        try:
            assert _parse_config_model(path) is None
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        """Missing file → None."""
        assert _parse_config_model("/nonexistent/config.yaml") is None

    def test_invalid_yaml(self):
        """Invalid YAML → None."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(": bad yaml :\n")
            path = f.name
        try:
            assert _parse_config_model(path) is None
        finally:
            os.unlink(path)


# ===========================================================================
# Profile discovery
# ===========================================================================

class TestDiscoverProfiles:
    """discover_profiles finds SOUL.md files under ~/.hermes/profiles/."""

    def test_discover_real_profiles(self):
        """Real Hermes profiles are found (coder, editor, planner, researcher)."""
        profiles = list(discover_profiles())
        ids = {p[0] for p in profiles}
        expected = {"coder", "editor", "planner", "researcher"}
        assert expected.issubset(ids), f"Missing profiles: {expected - ids}"
        for pid, soul_path, config_path in profiles:
            assert soul_path.exists(), f"{soul_path} missing"
            assert soul_path.name == "SOUL.md"
            assert config_path.name == "config.yaml"

    def test_skip_dot_dirs(self):
        """Directories starting with '.' are skipped."""
        profiles = list(discover_profiles())
        ids = {p[0] for p in profiles}
        assert not any(i.startswith(".") for i in ids)


# ===========================================================================
# Role and color mappings
# ===========================================================================

class TestRoleColorMappings:
    """PROFILE_ROLES and PROFILE_COLORS match expected values."""

    def test_role_mapping(self):
        assert PROFILE_ROLES["coder"] == "implementation"
        assert PROFILE_ROLES["editor"] == "quality"
        assert PROFILE_ROLES["planner"] == "architecture"
        assert PROFILE_ROLES["researcher"] == "research"
        assert PROFILE_ROLES["vesper"] == "creative"

    def test_color_mapping(self):
        assert PROFILE_COLORS["vesper"] == "#FFD700"  # gold
        assert PROFILE_COLORS["coder"] == "#E6E6FA"  # lavender
        assert PROFILE_COLORS["editor"] == "#FF007F"  # rose
        assert PROFILE_COLORS["researcher"] == "#7cacef"  # blue
        assert PROFILE_COLORS["planner"] == "#008080"  # teal


# ===========================================================================
# DB sync (integration)
# ===========================================================================

class TestSyncFromProfiles:
    """sync_from_profiles creates/updates Agent records in the database."""

    def test_sync_creates_agents(self, db, app):
        """Calling sync_from_profiles creates Agent records for each profile."""
        from agents.registry import sync_from_profiles
        from models import Agent

        with app.app_context():
            agents = sync_from_profiles(db=db)
            assert len(agents) >= 4  # coder, editor, planner, researcher

            names = {a.name for a in agents}
            assert "Coder" in names
            assert "Editor" in names
            assert "Planner" in names
            assert "Researcher" in names

    def test_sync_sets_personality(self, db, app):
        """Agent personality is extracted from SOUL.md."""
        from agents.registry import sync_from_profiles
        from models import Agent

        with app.app_context():
            sync_from_profiles(db=db)
            coder = db.session.query(Agent).filter_by(name="Coder").first()
            assert coder is not None
            assert "methodical" in coder.personality.lower()

            editor = db.session.query(Agent).filter_by(name="Editor").first()
            assert editor is not None
            assert "detail-oriented" in editor.personality.lower()

    def test_sync_sets_colors(self, db, app):
        """Agent avatar_color matches the PROFILE_COLORS mapping."""
        from agents.registry import sync_from_profiles
        from models import Agent

        with app.app_context():
            sync_from_profiles(db=db)

            coder = db.session.query(Agent).filter_by(name="Coder").first()
            assert coder.avatar_color == "#E6E6FA"

            editor = db.session.query(Agent).filter_by(name="Editor").first()
            assert editor.avatar_color == "#FF007F"

            planner = db.session.query(Agent).filter_by(name="Planner").first()
            assert planner.avatar_color == "#008080"

            researcher = db.session.query(Agent).filter_by(name="Researcher").first()
            assert researcher.avatar_color == "#7cacef"

    def test_sync_sets_model(self, db, app):
        """Agent capabilities include expected items (model config is parsed but
        not stored directly on Agent model — only personality/color/role)."""
        from agents.registry import sync_from_profiles
        from models import Agent

        with app.app_context():
            sync_from_profiles(db=db)
            coder = db.session.query(Agent).filter_by(name="Coder").first()
            assert len(coder.capabilities) > 0

    def test_sync_idempotent(self, db, app):
        """Calling sync_from_profiles twice does not duplicate agents."""
        from agents.registry import sync_from_profiles
        from models import Agent

        with app.app_context():
            sync_from_profiles(db=db)
            count1 = db.session.query(Agent).count()

            sync_from_profiles(db=db)
            count2 = db.session.query(Agent).count()

            assert count2 == count1

    def test_sync_updates_existing(self, db, app):
        """Existing agents get their fields updated from profile changes."""
        from agents.registry import sync_from_profiles
        from models import Agent

        with app.app_context():
            # First sync
            sync_from_profiles(db=db)
            coder = db.session.query(Agent).filter_by(name="Coder").first()
            old_personality = coder.personality

            # Second sync — same profiles, shouldn't change
            sync_from_profiles(db=db)
            coder = db.session.query(Agent).filter_by(name="Coder").first()
            assert coder.personality == old_personality


# ===========================================================================
# sync_agents (high-level entry point)
# ===========================================================================

class TestSyncAgents:
    """sync_agents combines DB sync with registry population."""

    def test_sync_agents_populates_registry(self, db, app):
        """sync_agents returns agent records and keeps registry intact."""
        from agents.registry import sync_agents, default_registry

        with app.app_context():
            agents = sync_agents(db=db)

            # Should have DB records
            assert len(agents) >= 4

            # Registry should still have all standard agents
            reg_ids = {a.id for a in default_registry.list()}
            assert "vesper" in reg_ids
            assert "coder" in reg_ids
            assert "editor" in reg_ids
            assert "planner" in reg_ids
            assert "researcher" in reg_ids

    def test_sync_agents_returns_list(self, db, app):
        """sync_agents returns a list of Agent model instances."""
        from agents.registry import sync_agents

        with app.app_context():
            agents = sync_agents(db=db)
            assert isinstance(agents, list)
            if agents:
                from models import Agent
                assert isinstance(agents[0], Agent)
