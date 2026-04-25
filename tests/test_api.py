"""Tests for the REST API blueprint."""
import json


# ---------------------------------------------------------------------------
# Fixtures shared across test classes
# ---------------------------------------------------------------------------


def _seed_agents(db):
    """Create a couple of agents for testing."""
    from models import Agent

    a1 = Agent(
        name="Alpha",
        role="worker",
        personality="diligent",
        capabilities=["research", "write"],
        status="online",
        avatar_color="#FF0000",
    )
    a2 = Agent(
        name="Beta",
        role="worker",
        personality="analytical",
        capabilities=["review", "test"],
        status="offline",
        avatar_color="#00FF00",
    )
    db.session.add_all([a1, a2])
    db.session.commit()
    return a1, a2


def _seed_conversation(db, agents):
    """Create a conversation between agents."""
    from models import Conversation

    conv = Conversation(title="Test Chat", participants=list(agents))
    db.session.add(conv)
    db.session.commit()
    return conv


def _seed_message(db, sender, receiver, conversation, **kw):
    """Create a message."""
    from models import Message

    msg = Message(
        from_agent_id=sender.id,
        to_agent_id=receiver.id,
        conversation_id=conversation.id,
        type=kw.get("type", "text"),
        priority=kw.get("priority", "normal"),
        status=kw.get("status", "sent"),
        subject=kw.get("subject", "Hello"),
        body=kw.get("body", "Body text"),
    )
    db.session.add(msg)
    db.session.commit()
    return msg


def _seed_note(db, agent, **kw):
    """Create a note for an agent."""
    from models import Note

    note = Note(
        agent_id=agent.id,
        title=kw.get("title", "My Note"),
        body=kw.get("body", "Note body"),
        tags=kw.get("tags", []),
        pinned=kw.get("pinned", False),
    )
    db.session.add(note)
    db.session.commit()
    return note


# ===================================================================
# Agent API tests
# ===================================================================


class TestListAgents:
    """GET /api/agents"""

    def test_empty(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        assert resp.json == []

    def test_returns_all_agents(self, client, db):
        _seed_agents(db)
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        assert len(resp.json) == 2
        names = {a["name"] for a in resp.json}
        assert names == {"Alpha", "Beta"}

    def test_serialization_fields(self, client, db):
        _seed_agents(db)
        resp = client.get("/api/agents")
        agent = resp.json[0]
        assert "id" in agent
        assert "name" in agent
        assert "role" in agent
        assert "status" in agent
        assert "created_at" in agent


class TestGetAgent:
    """GET /api/agents/<id>"""

    def test_not_found(self, client):
        resp = client.get("/api/agents/999")
        assert resp.status_code == 404
        assert resp.json["error"] == "Agent not found"

    def test_returns_agent(self, client, db):
        agents, _ = _seed_agents(db)
        a1 = agents
        resp = client.get(f"/api/agents/{a1.id}")
        assert resp.status_code == 200
        assert resp.json["name"] == "Alpha"
        assert resp.json["status"] == "online"

    def test_includes_recent_messages(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv, subject="Msg1")
        _seed_message(db, a2, a1, conv, subject="Msg2")

        resp = client.get(f"/api/agents/{a1.id}")
        assert resp.status_code == 200
        assert "recent_messages" in resp.json
        assert len(resp.json["recent_messages"]) == 2


class TestUpdateAgentStatus:
    """PUT /api/agents/<id>/status"""

    def test_not_found(self, client):
        resp = client.put(
            "/api/agents/999/status",
            json={"status": "busy"},
        )
        assert resp.status_code == 404

    def test_missing_status(self, client, db):
        a1, _ = _seed_agents(db)
        resp = client.put(f"/api/agents/{a1.id}/status", json={})
        assert resp.status_code == 400
        assert "status" in resp.json["error"]

    def test_missing_body(self, client, db):
        a1, _ = _seed_agents(db)
        resp = client.put(
            f"/api/agents/{a1.id}/status",
            content_type="application/json",
            data="",
        )
        assert resp.status_code == 400

    def test_updates_status(self, client, db):
        a1, _ = _seed_agents(db)
        assert a1.status == "online"

        resp = client.put(
            f"/api/agents/{a1.id}/status",
            json={"status": "busy"},
        )
        assert resp.status_code == 200
        assert resp.json["status"] == "busy"

        # Verify db is updated
        from models import Agent

        from app import db as _db

        _db.session.expire_all()
        updated = _db.session.get(Agent, a1.id)
        assert updated.status == "busy"
        assert updated.last_seen is not None

    def test_updates_last_seen(self, client, db):
        a1, _ = _seed_agents(db)
        assert a1.last_seen is None

        client.put(f"/api/agents/{a1.id}/status", json={"status": "online"})

        from models import Agent
        from app import db as _db

        _db.session.expire_all()
        updated = _db.session.get(Agent, a1.id)
        assert updated.last_seen is not None


# ===================================================================
# Message API tests
# ===================================================================


class TestListMessages:
    """GET /api/messages"""

    def test_empty(self, client):
        resp = client.get("/api/messages")
        assert resp.status_code == 200
        assert resp.json == []

    def test_all_messages(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv)
        _seed_message(db, a2, a1, conv, subject="Reply")

        resp = client.get("/api/messages")
        assert resp.status_code == 200
        assert len(resp.json) == 2

    def test_filter_by_agent_id(self, client, db):
        from models import Agent

        a1 = Agent(name="Alpha", role="worker")
        a2 = Agent(name="Beta", role="worker")
        a3 = Agent(name="Gamma", role="observer")
        db.session.add_all([a1, a2, a3])
        db.session.commit()

        conv1 = _seed_conversation(db, [a1, a2])
        conv2 = _seed_conversation(db, [a1, a3])
        _seed_message(db, a1, a2, conv1, subject="To Beta")
        _seed_message(db, a1, a3, conv2, subject="To Gamma")

        resp = client.get(f"/api/messages?agent_id={a2.id}")
        assert resp.status_code == 200
        assert len(resp.json) == 1
        assert resp.json[0]["subject"] == "To Beta"

    def test_filter_by_type(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv, type="text", subject="Text msg")
        _seed_message(db, a1, a2, conv, type="alert", subject="Alert msg")

        resp = client.get("/api/messages?type=alert")
        assert resp.status_code == 200
        assert len(resp.json) == 1
        assert resp.json[0]["type"] == "alert"

    def test_filter_by_status(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv, status="sent")
        _seed_message(db, a1, a2, conv, status="delivered", subject="Delivered")

        resp = client.get("/api/messages?status=delivered")
        assert resp.status_code == 200
        assert len(resp.json) == 1
        assert resp.json[0]["subject"] == "Delivered"

    def test_filter_combined(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv, type="alert", status="sent", subject="Alert")
        _seed_message(db, a1, a2, conv, type="text", status="sent", subject="Text")

        resp = client.get(f"/api/messages?agent_id={a1.id}&type=alert&status=sent")
        assert resp.status_code == 200
        assert len(resp.json) >= 1


class TestSendMessage:
    """POST /api/messages"""

    def test_missing_body(self, client):
        resp = client.post(
            "/api/messages",
            content_type="application/json",
            data="",
        )
        assert resp.status_code == 400

    def test_missing_required_fields(self, client, db):
        resp = client.post("/api/messages", json={"from_agent_id": 1})
        assert resp.status_code == 400

    def test_nonexistent_agent(self, client, db):
        a1, _ = _seed_agents(db)
        resp = client.post(
            "/api/messages",
            json={
                "from_agent_id": a1.id,
                "to_agent_id": 999,
                "type": "text",
                "subject": "Hi",
                "body": "Hello",
            },
        )
        assert resp.status_code == 404

    def test_sends_message(self, client, db):
        a1, a2 = _seed_agents(db)
        resp = client.post(
            "/api/messages",
            json={
                "from_agent_id": a1.id,
                "to_agent_id": a2.id,
                "type": "text",
                "subject": "Greetings",
                "body": "Hello from Alpha!",
            },
        )
        assert resp.status_code == 201
        data = resp.json
        assert data["from_agent_id"] == a1.id
        assert data["to_agent_id"] == a2.id
        assert data["type"] == "text"
        assert data["subject"] == "Greetings"
        assert data["body"] == "Hello from Alpha!"
        assert data["priority"] == "normal"
        assert data["status"] == "sent"

    def test_sends_with_priority(self, client, db):
        a1, a2 = _seed_agents(db)
        resp = client.post(
            "/api/messages",
            json={
                "from_agent_id": a1.id,
                "to_agent_id": a2.id,
                "type": "alert",
                "subject": "Urgent",
                "body": "High priority!",
                "priority": "high",
            },
        )
        assert resp.status_code == 201
        assert resp.json["priority"] == "high"

    def test_creates_direct_conversation(self, client, db):
        """Sending a message creates a direct conversation automatically."""
        from models import Conversation

        a1, a2 = _seed_agents(db)
        assert Conversation.query.count() == 0

        client.post(
            "/api/messages",
            json={
                "from_agent_id": a1.id,
                "to_agent_id": a2.id,
                "type": "text",
                "subject": "Hi",
                "body": "Body",
            },
        )

        assert Conversation.query.count() == 1
        conv = Conversation.query.first()
        assert a1 in conv.participants
        assert a2 in conv.participants

    def test_reuses_existing_conversation(self, client, db):
        """Multiple messages reuse the same direct conversation."""
        from models import Conversation

        a1, a2 = _seed_agents(db)

        client.post(
            "/api/messages",
            json={
                "from_agent_id": a1.id,
                "to_agent_id": a2.id,
                "type": "text",
                "subject": "First",
                "body": "First msg",
            },
        )
        client.post(
            "/api/messages",
            json={
                "from_agent_id": a2.id,
                "to_agent_id": a1.id,
                "type": "text",
                "subject": "Second",
                "body": "Second msg",
            },
        )

        assert Conversation.query.count() == 1


class TestMarkRead:
    """PUT /api/messages/<id>/read"""

    def test_not_found(self, client):
        resp = client.put("/api/messages/999/read")
        assert resp.status_code == 404

    def test_marks_read(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        assert msg.read_at is None
        resp = client.put(f"/api/messages/{msg.id}/read")
        assert resp.status_code == 200
        assert resp.json["read_at"] is not None


class TestMarkAcknowledged:
    """PUT /api/messages/<id>/acknowledge"""

    def test_not_found(self, client):
        resp = client.put("/api/messages/999/acknowledge")
        assert resp.status_code == 404

    def test_marks_acknowledged(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        assert msg.acknowledged_at is None
        resp = client.put(f"/api/messages/{msg.id}/acknowledge")
        assert resp.status_code == 200
        assert resp.json["acknowledged_at"] is not None


# ===================================================================
# Conversation API tests
# ===================================================================


class TestListConversations:
    """GET /api/conversations"""

    def test_empty(self, client):
        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        assert resp.json == []

    def test_returns_all(self, client, db):
        a1, a2 = _seed_agents(db)
        _seed_conversation(db, [a1])
        _seed_conversation(db, [a1, a2])

        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        assert len(resp.json) == 2

    def test_serialization(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])

        resp = client.get("/api/conversations")
        data = resp.json[0]
        assert data["id"] == conv.id
        assert data["title"] == "Test Chat"
        assert set(data["participants"]) == {a1.id, a2.id}
        assert "created_at" in data
        assert "updated_at" in data


class TestCreateConversation:
    """POST /api/conversations"""

    def test_missing_title(self, client):
        resp = client.post("/api/conversations", json={})
        assert resp.status_code == 400

    def test_missing_body(self, client):
        resp = client.post(
            "/api/conversations",
            content_type="application/json",
            data="",
        )
        assert resp.status_code == 400

    def test_creates_with_title_only(self, client, db):
        resp = client.post(
            "/api/conversations",
            json={"title": "Empty Room"},
        )
        assert resp.status_code == 201
        assert resp.json["title"] == "Empty Room"
        assert resp.json["participants"] == []

    def test_creates_with_participants(self, client, db):
        a1, a2 = _seed_agents(db)
        resp = client.post(
            "/api/conversations",
            json={"title": "Team Chat", "participants": [a1.id, a2.id]},
        )
        assert resp.status_code == 201
        assert resp.json["title"] == "Team Chat"
        assert set(resp.json["participants"]) == {a1.id, a2.id}

    def test_persists_in_db(self, client, db):
        from models import Conversation

        a1, a2 = _seed_agents(db)
        client.post(
            "/api/conversations",
            json={"title": "Persist", "participants": [a1.id, a2.id]},
        )
        assert Conversation.query.count() == 1
        conv = Conversation.query.first()
        assert conv.title == "Persist"


class TestGetConversationMessages:
    """GET /api/conversations/<id>/messages"""

    def test_not_found(self, client):
        resp = client.get("/api/conversations/999/messages")
        assert resp.status_code == 404

    def test_empty_conversation(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])

        resp = client.get(f"/api/conversations/{conv.id}/messages")
        assert resp.status_code == 200
        assert resp.json == []

    def test_returns_messages_in_order(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        m1 = _seed_message(db, a1, a2, conv, subject="First")
        m2 = _seed_message(db, a2, a1, conv, subject="Second")

        resp = client.get(f"/api/conversations/{conv.id}/messages")
        assert resp.status_code == 200
        assert len(resp.json) == 2
        # Messages ordered by created_at ascending
        assert resp.json[0]["subject"] == "First"
        assert resp.json[1]["subject"] == "Second"


# ===================================================================
# Note API tests
# ===================================================================


class TestListNotes:
    """GET /api/notes"""

    def test_empty(self, client):
        resp = client.get("/api/notes")
        assert resp.status_code == 200
        assert resp.json == []

    def test_all_notes(self, client, db):
        a1, a2 = _seed_agents(db)
        _seed_note(db, a1, title="A1 Note")
        _seed_note(db, a2, title="A2 Note")

        resp = client.get("/api/notes")
        assert resp.status_code == 200
        assert len(resp.json) == 2

    def test_filter_by_agent_id(self, client, db):
        a1, a2 = _seed_agents(db)
        _seed_note(db, a1, title="Alpha Note")
        _seed_note(db, a2, title="Beta Note")

        resp = client.get(f"/api/notes?agent_id={a1.id}")
        assert resp.status_code == 200
        assert len(resp.json) == 1
        assert resp.json[0]["title"] == "Alpha Note"

    def test_filter_by_pinned(self, client, db):
        a1, _ = _seed_agents(db)
        _seed_note(db, a1, title="Normal", pinned=False)
        _seed_note(db, a1, title="Pinned!", pinned=True)

        resp = client.get("/api/notes?pinned=true")
        assert resp.status_code == 200
        assert len(resp.json) == 1
        assert resp.json[0]["pinned"] is True

    def test_filter_by_agent_and_pinned(self, client, db):
        a1, a2 = _seed_agents(db)
        _seed_note(db, a1, title="A1 Normal", pinned=False)
        _seed_note(db, a1, title="A1 Pinned", pinned=True)
        _seed_note(db, a2, title="A2 Pinned", pinned=True)

        resp = client.get(f"/api/notes?agent_id={a1.id}&pinned=true")
        assert resp.status_code == 200
        assert len(resp.json) == 1
        assert resp.json[0]["title"] == "A1 Pinned"


class TestCreateNote:
    """POST /api/notes"""

    def test_missing_body(self, client):
        resp = client.post(
            "/api/notes",
            content_type="application/json",
            data="",
        )
        assert resp.status_code == 400

    def test_missing_agent_id(self, client, db):
        resp = client.post("/api/notes", json={"title": "No Agent"})
        assert resp.status_code == 400

    def test_missing_title(self, client, db):
        a1, _ = _seed_agents(db)
        resp = client.post("/api/notes", json={"agent_id": a1.id})
        assert resp.status_code == 400

    def test_creates_note(self, client, db):
        a1, _ = _seed_agents(db)
        resp = client.post(
            "/api/notes",
            json={
                "agent_id": a1.id,
                "title": "Research Notes",
                "body": "Important findings",
                "tags": ["research", "important"],
                "pinned": True,
            },
        )
        assert resp.status_code == 201
        data = resp.json
        assert data["agent_id"] == a1.id
        assert data["title"] == "Research Notes"
        assert data["body"] == "Important findings"
        assert data["tags"] == ["research", "important"]
        assert data["pinned"] is True

    def test_creates_with_defaults(self, client, db):
        a1, _ = _seed_agents(db)
        resp = client.post(
            "/api/notes",
            json={
                "agent_id": a1.id,
                "title": "Minimal Note",
            },
        )
        assert resp.status_code == 201
        data = resp.json
        assert data["title"] == "Minimal Note"
        assert data["body"] is None
        assert data["tags"] == []
        assert data["pinned"] is False

    def test_persists_in_db(self, client, db):
        from models import Note

        a1, _ = _seed_agents(db)
        client.post(
            "/api/notes",
            json={"agent_id": a1.id, "title": "Persist Note", "body": "Body"},
        )

        assert Note.query.count() == 1
        note = Note.query.first()
        assert note.title == "Persist Note"
        assert note.body == "Body"
        assert note.agent_id == a1.id


# ===================================================================
# Stats API tests
# ===================================================================


class TestGetStats:
    """GET /api/stats"""

    def test_empty_stats(self, client, db):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert resp.json == {
            "total_agents": 0,
            "unread_messages": 0,
            "active_conversations": 0,
        }

    def test_counts_agents(self, client, db):
        _seed_agents(db)
        resp = client.get("/api/stats")
        assert resp.json["total_agents"] == 2

    def test_counts_unread_messages(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv)
        _seed_message(db, a1, a2, conv, subject="Second")

        resp = client.get("/api/stats")
        assert resp.json["unread_messages"] == 2

    def test_counts_read_message_as_not_unread(self, client, db):
        from datetime import datetime, timezone
        from models import Message

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv)

        # Manually mark one as read
        msg = Message.query.first()
        msg.read_at = datetime.now(timezone.utc)
        db.session.commit()

        resp = client.get("/api/stats")
        assert resp.json["unread_messages"] == 0

    def test_counts_conversations(self, client, db):
        a1, a2 = _seed_agents(db)
        _seed_conversation(db, [a1])
        _seed_conversation(db, [a1, a2])

        resp = client.get("/api/stats")
        assert resp.json["active_conversations"] == 2

    def test_all_counts_together(self, client, db):
        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv)
        _seed_message(db, a2, a1, conv, subject="Reply")

        resp = client.get("/api/stats")
        assert resp.json == {
            "total_agents": 2,
            "unread_messages": 2,
            "active_conversations": 1,
        }
