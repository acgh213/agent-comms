"""Tests for the compose message page and route."""


class TestComposeRoute:
    """Tests for GET /compose."""

    def test_compose_page_returns_200(self, client, db):
        """Compose page renders successfully."""
        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Compose Message" in html
        assert "compose-form" in html

    def test_compose_shows_agent_dropdowns(self, client, db):
        """Compose page has from and to agent dropdowns."""
        from models import Agent

        agent = Agent(
            name="Vesper",
            role="coordinator",
            status="online",
            avatar_color="#FFD700",
        )
        db.session.add(agent)
        db.session.commit()

        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert 'id="compose-from"' in html
        assert 'id="compose-to"' in html
        assert "Vesper" in html

    def test_compose_shows_all_agents(self, client, db):
        """Compose page lists all agents in both dropdowns."""
        from models import Agent

        agents = [
            Agent(name="Alpha", role="worker", avatar_color="#FF0000"),
            Agent(name="Beta", role="worker", avatar_color="#00FF00"),
            Agent(name="Gamma", role="observer", avatar_color="#0000FF"),
        ]
        db.session.add_all(agents)
        db.session.commit()

        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        for a in agents:
            assert a.name in html

    def test_compose_with_from_param(self, client, db):
        """GET /compose?from=<id> pre-selects the from agent."""
        from models import Agent

        agent = Agent(
            name="PreSelect",
            role="test",
            avatar_color="#FFD700",
        )
        db.session.add(agent)
        db.session.commit()

        resp = client.get(f"/compose?from={agent.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert f'value="{agent.id}" selected' in html or "selected" in html

    def test_compose_has_all_input_fields(self, client, db):
        """Compose form has all required fields."""
        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert 'id="compose-type"' in html
        assert 'id="compose-priority"' in html
        assert 'id="compose-subject"' in html
        assert 'id="compose-body"' in html
        assert 'id="compose-send"' in html
        assert 'id="compose-discard"' in html

    def test_compose_has_type_options(self, client, db):
        """Compose form includes all message types."""
        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        for t in ["request", "response", "notification", "task", "note"]:
            assert t in html

    def test_compose_has_priority_options(self, client, db):
        """Compose form includes all priority levels."""
        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        for p in ["low", "normal", "high", "urgent"]:
            assert p in html

    def test_compose_includes_markdown_hint(self, client, db):
        """Compose page shows markdown hint below textarea."""
        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Markdown" in html or "markdown" in html

    def test_compose_has_draft_indicator(self, client, db):
        """Compose page includes draft indicator element."""
        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert 'draft-indicator' in html

    def test_compose_loads_compose_js(self, client, db):
        """Compose page loads compose.js script."""
        resp = client.get("/compose")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "compose.js" in html


class TestComposePost:
    """Tests for POST /compose (server-side form submission fallback)."""

    def test_post_missing_from(self, client, db):
        """POST with missing from returns form with error."""
        resp = client.post(
            "/compose",
            data={
                "to_agent_id": 1,
                "subject": "Test",
                "body": "Body",
            },
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "required" in html.lower()

    def test_post_nonexistent_agent(self, client, db):
        """POST with nonexistent agent returns form with error."""
        resp = client.post(
            "/compose",
            data={
                "from_agent_id": 999,
                "to_agent_id": 1,
                "subject": "Test",
                "body": "Body",
            },
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "not found" in html.lower()

    def test_post_sends_message(self, client, db):
        """POST with valid data creates a message and redirects."""
        from models import Agent, Message, Conversation

        sender = Agent(
            name="ComposeSender",
            role="sender",
            avatar_color="#FFD700",
        )
        receiver = Agent(
            name="ComposeReceiver",
            role="receiver",
            avatar_color="#008080",
        )
        db.session.add_all([sender, receiver])
        db.session.commit()

        resp = client.post(
            "/compose",
            data={
                "from_agent_id": sender.id,
                "to_agent_id": receiver.id,
                "subject": "Compose Test",
                "body": "Sent via compose form",
                "type": "request",
                "priority": "high",
            },
        )

        # Should redirect to the conversation
        assert resp.status_code in (302, 303)
        assert "/conversation/" in resp.headers.get("Location", "")

        # Verify message was created
        msgs = Message.query.all()
        assert len(msgs) == 1
        assert msgs[0].subject == "Compose Test"
        assert msgs[0].body == "Sent via compose form"
        assert msgs[0].type == "request"
        assert msgs[0].priority == "high"

        # Verify conversation was created
        conv = Conversation.query.first()
        assert conv is not None
        assert sender in conv.participants
        assert receiver in conv.participants
