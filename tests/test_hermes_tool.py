"""Tests for the Hermes integration tool (hermes_tool.py).

All tests use the shared test app/DB via ``hermes_tool.configure(app)`` so that
the tool operates on the same in-memory SQLite database as the test fixtures.
"""
import pytest


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_agents(db):
    """Create a couple of agents for testing."""
    from models import Agent

    a1 = Agent(name="Alice", role="worker", status="online")
    a2 = Agent(name="Bob", role="worker", status="offline")
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


# ===================================================================
# Fixture: configure hermes_tool to use the test app
# ===================================================================


@pytest.fixture(autouse=True)
def configure_hermes_tool(app):
    """Point hermes_tool at the test app so it uses the in-memory DB."""
    import hermes_tool

    hermes_tool.configure(app)
    yield


# ===================================================================
# Test: send_message
# ===================================================================


class TestSendMessage:
    """send_message(to_name, subject, body, msg_type, priority)"""

    def test_sends_message_to_named_agent(self, db):
        """Message is created successfully when recipient exists."""
        from hermes_tool import send_message
        from models import Agent

        _seed_agents(db)

        result = send_message(
            to_name="Bob",
            subject="Greetings",
            body="Hello Bob!",
            msg_type="request",
            priority="high",
        )

        assert "error" not in result
        assert result["subject"] == "Greetings"
        assert result["body"] == "Hello Bob!"
        assert result["type"] == "request"
        assert result["priority"] == "high"

        # Verify sender is "hermes" (auto-created)
        hermes = Agent.query.filter_by(name="hermes").first()
        assert hermes is not None
        assert result["from_agent_id"] == hermes.id

        # Verify recipient is Bob
        bob = Agent.query.filter_by(name="Bob").first()
        assert bob is not None
        assert result["to_agent_id"] == bob.id

    def test_auto_registers_sender(self, db):
        """The hermes agent is auto-created if it doesn't exist."""
        from hermes_tool import send_message
        from models import Agent

        _seed_agents(db)

        assert Agent.query.filter_by(name="hermes").count() == 0
        send_message(to_name="Alice", subject="Hi", body="Test")
        assert Agent.query.filter_by(name="hermes").count() == 1

    def test_auto_registers_recipient(self, db):
        """Recipient is auto-created if they don't exist."""
        from hermes_tool import send_message
        from models import Agent

        assert Agent.query.filter_by(name="NewAgent").count() == 0
        send_message(to_name="NewAgent", subject="Welcome", body="Hello!")
        assert Agent.query.filter_by(name="NewAgent").count() == 1

    def test_creates_direct_conversation(self, db):
        """Sending creates a direct conversation automatically."""
        from hermes_tool import send_message
        from models import Conversation

        result = send_message(
            to_name="Charlie", subject="Hi", body="Let's chat"
        )
        assert "error" not in result
        assert result["conversation_id"] is not None

        conv = db.session.get(Conversation, result["conversation_id"])
        assert conv is not None
        assert len(conv.participants) == 2

    def test_reuses_existing_conversation(self, db):
        """Multiple sends reuse the same conversation."""
        from hermes_tool import send_message
        from models import Conversation

        r1 = send_message(to_name="Dave", subject="First", body="Msg 1")
        r2 = send_message(to_name="Dave", subject="Second", body="Msg 2")

        assert r1["conversation_id"] == r2["conversation_id"]
        assert Conversation.query.count() == 1

    def test_default_type_and_priority(self, db):
        """Defaults are applied when not specified."""
        from hermes_tool import send_message

        result = send_message(
            to_name="Eve", subject="Defaults", body="test"
        )
        assert result["type"] == "request"
        assert result["priority"] == "normal"

    def test_returns_dict_not_model(self, db):
        """Result is a plain Python dict."""
        from hermes_tool import send_message

        result = send_message(
            to_name="Frank", subject="Check", body="Test"
        )
        assert isinstance(result, dict)
        assert "id" in result
        assert "created_at" in result


# ===================================================================
# Test: check_messages
# ===================================================================


class TestCheckMessages:
    """check_messages(agent_name=None)"""

    def test_no_unread_returns_empty(self, db):
        """No unread messages returns []."""
        from hermes_tool import check_messages

        assert check_messages("Alice") == []

    def test_returns_unread_for_agent(self, db):
        """Unread messages for a specific agent are returned."""
        from hermes_tool import check_messages

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv, subject="Unread Msg")

        results = check_messages("Bob")
        assert len(results) == 1
        assert results[0]["subject"] == "Unread Msg"
        assert results[0]["to_agent_id"] == a2.id

    def test_excludes_read_messages(self, db):
        """Read messages are excluded from unread."""
        from hermes_tool import check_messages, read_message

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv, subject="Read Me")

        # Mark as read
        read_message(msg.id)

        results = check_messages("Bob")
        assert len(results) == 0

    def test_unknown_agent_returns_empty(self, db):
        """Querying for a non-existent agent returns []."""
        from hermes_tool import check_messages

        assert check_messages("Ghost") == []

    def test_returns_all_unread_when_no_name(self, db):
        """When agent_name is None, all unread across agents are returned."""
        from hermes_tool import check_messages

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        _seed_message(db, a1, a2, conv, subject="Msg 1")
        _seed_message(db, a2, a1, conv, subject="Msg 2")

        results = check_messages()
        assert len(results) == 2


# ===================================================================
# Test: read_message
# ===================================================================


class TestReadMessage:
    """read_message(message_id)"""

    def test_marks_message_as_read(self, db):
        """read_at is set on the message."""
        from hermes_tool import read_message

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = read_message(msg.id)
        assert "error" not in result
        assert result["read_at"] is not None

    def test_not_found_returns_error(self, db):
        """Non-existent message returns error dict."""
        from hermes_tool import read_message

        result = read_message(9999)
        assert "error" in result
        assert result["error"] == "Message not found"

    def test_returns_plain_dict(self, db):
        """Result is a dict, not a model."""
        from hermes_tool import read_message

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = read_message(msg.id)
        assert isinstance(result, dict)


# ===================================================================
# Test: acknowledge_message
# ===================================================================


class TestAcknowledgeMessage:
    """acknowledge_message(message_id)"""

    def test_marks_message_as_acknowledged(self, db):
        """acknowledged_at is set on the message."""
        from hermes_tool import acknowledge_message

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = acknowledge_message(msg.id)
        assert "error" not in result
        assert result["acknowledged_at"] is not None

    def test_not_found_returns_error(self, db):
        """Non-existent message returns error dict."""
        from hermes_tool import acknowledge_message

        result = acknowledge_message(9999)
        assert "error" in result
        assert result["error"] == "Message not found"

    def test_returns_plain_dict(self, db):
        """Result is a dict, not a model."""
        from hermes_tool import acknowledge_message

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = acknowledge_message(msg.id)
        assert isinstance(result, dict)


# ===================================================================
# Test: leave_note
# ===================================================================


class TestLeaveNote:
    """leave_note(title, body, tags, pinned)"""

    def test_creates_note(self, db):
        """Note is created with given fields."""
        from hermes_tool import leave_note

        result = leave_note(
            title="Research Update",
            body="Found something interesting",
            tags=["research", "important"],
            pinned=True,
        )

        assert "error" not in result
        assert result["title"] == "Research Update"
        assert result["body"] == "Found something interesting"
        assert result["tags"] == ["research", "important"]
        assert result["pinned"] is True

    def test_associates_with_hermes_agent(self, db):
        """Note belongs to the hermes agent."""
        from hermes_tool import leave_note
        from models import Agent

        result = leave_note(title="Test Note", body="Body")
        hermes = Agent.query.filter_by(name="hermes").first()
        assert hermes is not None
        assert result["agent_id"] == hermes.id

    def test_defaults(self, db):
        """Defaults are applied for optional fields."""
        from hermes_tool import leave_note

        result = leave_note(title="Minimal", body="Just a note")
        assert result["tags"] == []
        assert result["pinned"] is False

    def test_empty_tags(self, db):
        """Explicit empty tags list works."""
        from hermes_tool import leave_note

        result = leave_note(title="Tags Empty", body="Body", tags=[])
        assert result["tags"] == []

    def test_returns_plain_dict(self, db):
        """Result is a dict, not a model."""
        from hermes_tool import leave_note

        result = leave_note(title="Dict Check", body="Body")
        assert isinstance(result, dict)

    def test_persists_in_db(self, db):
        """Note is actually saved to the database."""
        from hermes_tool import leave_note
        from models import Note

        result = leave_note(title="Persist", body="Check DB")
        note = db.session.get(Note, result["id"])
        assert note is not None
        assert note.title == "Persist"
        assert note.body == "Check DB"


# ===================================================================
# Test: get_conversations
# ===================================================================


class TestGetConversations:
    """get_conversations(agent_name=None)"""

    def test_empty_returns_empty_list(self, db):
        """No conversations returns []."""
        from hermes_tool import get_conversations

        assert get_conversations() == []

    def test_returns_all_when_no_name(self, db):
        """All conversations returned when agent_name is None."""
        from hermes_tool import get_conversations

        a1, a2 = _seed_agents(db)
        _seed_conversation(db, [a1])
        _seed_conversation(db, [a1, a2])

        results = get_conversations()
        assert len(results) == 2

    def test_filters_by_agent_name(self, db):
        """Only conversations with that agent are returned."""
        from hermes_tool import get_conversations

        a1, a2 = _seed_agents(db)
        # Create one with a1 only
        _seed_conversation(db, [a1])

        results = get_conversations("Alice")
        assert len(results) == 1

    def test_unknown_agent_returns_empty(self, db):
        """Querying for a non-existent agent returns []."""
        from hermes_tool import get_conversations

        assert get_conversations("Ghost") == []

    def test_serialization(self, db):
        """Conversation dict has expected fields."""
        from hermes_tool import get_conversations

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])

        results = get_conversations()
        data = results[0]
        assert data["id"] == conv.id
        assert data["title"] == "Test Chat"
        assert set(data["participants"]) == {a1.id, a2.id}
        assert "created_at" in data
        assert "updated_at" in data


# ===================================================================
# Test: reply_to
# ===================================================================


class TestReplyTo:
    """reply_to(message_id, body, msg_type, priority)"""

    def test_reply_creates_message_in_same_conversation(self, db):
        """Reply is in the same conversation as the original."""
        from hermes_tool import reply_to

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv, subject="Original")

        result = reply_to(msg.id, "This is my reply!")
        assert "error" not in result
        assert result["conversation_id"] == conv.id
        assert result["body"] == "This is my reply!"

    def test_reply_swaps_sender_and_receiver(self, db):
        """Reply goes from original recipient to original sender."""
        from hermes_tool import reply_to

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = reply_to(msg.id, "Reply")
        assert result["from_agent_id"] == a2.id  # Bob replies
        assert result["to_agent_id"] == a1.id  # To Alice

    def test_reply_adds_re_subject_prefix(self, db):
        """Reply subject is prefixed with 'Re: '."""
        from hermes_tool import reply_to

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv, subject="Status Check")

        result = reply_to(msg.id, "All good")
        assert result["subject"] == "Re: Status Check"

    def test_reply_has_custom_type_and_priority(self, db):
        """Custom msg_type and priority are honoured."""
        from hermes_tool import reply_to

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = reply_to(
            msg.id,
            "Urgent reply!",
            msg_type="alert",
            priority="high",
        )
        assert result["type"] == "alert"
        assert result["priority"] == "high"

    def test_reply_default_type(self, db):
        """Default reply type is 'response'."""
        from hermes_tool import reply_to

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = reply_to(msg.id, "Default type")
        assert result["type"] == "response"

    def test_not_found_returns_error(self, db):
        """Replying to a non-existent message returns error."""
        from hermes_tool import reply_to

        result = reply_to(9999, "Hello?")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_returns_plain_dict(self, db):
        """Result is a dict, not a model."""
        from hermes_tool import reply_to

        a1, a2 = _seed_agents(db)
        conv = _seed_conversation(db, [a1, a2])
        msg = _seed_message(db, a1, a2, conv)

        result = reply_to(msg.id, "Dict check")
        assert isinstance(result, dict)


# ===================================================================
# Test: error handling
# ===================================================================


class TestErrorHandling:
    """All functions return dicts with 'error' key on failure."""

    def test_send_message_error_returns_error_dict(self, db):
        """Even if something fails, a dict is always returned."""
        from hermes_tool import send_message

        result = send_message(
            to_name="Target",
            subject="Test",
            body="Body",
        )
        # Should succeed actually, but verify it returns a dict
        assert isinstance(result, dict)

    def test_check_messages_returns_list(self, db):
        """check_messages always returns a list."""
        from hermes_tool import check_messages

        result = check_messages("NonExistent")
        assert isinstance(result, list)

    def test_read_message_error_type(self, db):
        """read_message returns dict with error key on failure."""
        from hermes_tool import read_message

        result = read_message(-1)
        assert isinstance(result, dict)
        assert "error" in result

    def test_acknowledge_message_error_type(self, db):
        """acknowledge_message returns dict with error key on failure."""
        from hermes_tool import acknowledge_message

        result = acknowledge_message(-1)
        assert isinstance(result, dict)
        assert "error" in result
