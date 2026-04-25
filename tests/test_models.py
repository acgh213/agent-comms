"""Tests for database models."""
import json


class TestAgentModel:
    """Test the Agent model."""

    def test_create_agent(self, db):
        """Create an agent with all fields."""
        from models import Agent
        from datetime import datetime, timezone

        agent = Agent(
            name="TestBot",
            role="tester",
            personality="thorough and meticulous",
            capabilities=["testing", "validation", "reporting"],
            status="online",
            avatar_color="#FF5733",
        )
        db.session.add(agent)
        db.session.commit()

        assert agent.id is not None
        assert agent.name == "TestBot"
        assert agent.role == "tester"
        assert agent.personality == "thorough and meticulous"
        assert agent.capabilities == ["testing", "validation", "reporting"]
        assert agent.status == "online"
        assert agent.avatar_color == "#FF5733"
        assert isinstance(agent.created_at, datetime)
        assert agent.last_seen is None

    def test_agent_default_status(self, db):
        """Agent defaults to offline status."""
        from models import Agent

        agent = Agent(name="DefaultBot", role="helper")
        db.session.add(agent)
        db.session.commit()

        assert agent.status == "offline"

    def test_agent_json_serialization(self, db):
        """Capabilities stored as JSON in DB, returned as list."""
        from models import Agent

        agent = Agent(
            name="JSONBot",
            role="demo",
            capabilities=["skill_a", "skill_b"],
        )
        db.session.add(agent)
        db.session.commit()

        # Verify JSON storage
        import sqlalchemy as sa

        row = db.session.execute(
            sa.text("SELECT capabilities FROM agent WHERE id = :id"),
            {"id": agent.id},
        ).fetchone()
        stored = json.loads(row[0])
        assert stored == ["skill_a", "skill_b"]

    def test_agent_timestamps(self, db):
        """Created_at is set automatically."""
        from models import Agent

        agent = Agent(name="TimeBot", role="timekeeper")
        db.session.add(agent)
        db.session.commit()

        assert agent.created_at is not None

    def test_agent_repr(self, db):
        """Agent has useful __repr__."""
        from models import Agent

        agent = Agent(name="ReprBot", role="demo")
        db.session.add(agent)
        db.session.commit()

        assert "ReprBot" in repr(agent)
        assert "demo" in repr(agent)


class TestConversationModel:
    """Test the Conversation model."""

    def test_create_conversation(self, db):
        """Create a conversation with participants."""
        from models import Agent, Conversation

        agent1 = Agent(name="Alpha", role="worker")
        agent2 = Agent(name="Beta", role="worker")
        db.session.add_all([agent1, agent2])
        db.session.flush()

        conv = Conversation(
            title="Test Planning",
            participants=[agent1, agent2],
        )
        db.session.add(conv)
        db.session.commit()

        assert conv.id is not None
        assert conv.title == "Test Planning"
        assert len(conv.participants) == 2
        assert agent1 in conv.participants
        assert agent2 in conv.participants

    def test_conversation_timestamps(self, db):
        """Created_at and updated_at are set."""
        from models import Agent, Conversation
        from datetime import datetime, timezone

        agent = Agent(name="Solo", role="solo")
        db.session.add(agent)
        db.session.flush()

        conv = Conversation(title="Solo Chat", participants=[agent])
        db.session.add(conv)
        db.session.commit()

        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert isinstance(conv.created_at, datetime)

    def test_empty_participants(self, db):
        """Conversation can be created without participants."""
        from models import Conversation

        conv = Conversation(title="Empty Room")
        db.session.add(conv)
        db.session.commit()

        assert conv.participants == []

    def test_conversation_repr(self, db):
        """Conversation has useful __repr__."""
        from models import Conversation

        conv = Conversation(title="Repr Room")
        db.session.add(conv)
        db.session.commit()

        assert "Repr Room" in repr(conv)


class TestMessageModel:
    """Test the Message model."""

    def test_create_message(self, db):
        """Create a message between agents in a conversation."""
        from models import Agent, Conversation, Message

        sender = Agent(name="Sender", role="sender")
        receiver = Agent(name="Receiver", role="receiver")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Chat", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            priority="normal",
            status="sent",
            subject="Hello",
            body="Hello, Receiver!",
            attachments=[{"file": "doc.txt", "size": 1024}],
        )
        db.session.add(msg)
        db.session.commit()

        assert msg.id is not None
        assert msg.from_agent_id == sender.id
        assert msg.to_agent_id == receiver.id
        assert msg.conversation_id == conv.id
        assert msg.type == "text"
        assert msg.priority == "normal"
        assert msg.status == "sent"
        assert msg.subject == "Hello"
        assert msg.body == "Hello, Receiver!"
        assert msg.attachments == [{"file": "doc.txt", "size": 1024}]
        assert msg.created_at is not None
        assert msg.read_at is None
        assert msg.acknowledged_at is None

    def test_message_defaults(self, db):
        """Message gets sensible defaults."""
        from models import Agent, Conversation, Message

        sender = Agent(name="DefaultSender", role="sender")
        receiver = Agent(name="DefaultReceiver", role="receiver")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Default Chat", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="Hi",
            body="test",
        )
        db.session.add(msg)
        db.session.commit()

        assert msg.priority == "normal"
        assert msg.status == "sent"
        assert msg.attachments == []

    def test_message_relationships(self, db):
        """Message has relationships to sender, receiver, and conversation."""
        from models import Agent, Conversation, Message

        sender = Agent(name="RelSender", role="sender")
        receiver = Agent(name="RelReceiver", role="receiver")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Rel Chat", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="Hello",
            body="World",
        )
        db.session.add(msg)
        db.session.commit()

        assert msg.sender.name == "RelSender"
        assert msg.receiver.name == "RelReceiver"
        assert msg.conversation.title == "Rel Chat"

    def test_message_repr(self, db):
        """Message has useful __repr__."""
        from models import Agent, Conversation, Message

        sender = Agent(name="S", role="s")
        receiver = Agent(name="R", role="r")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="C", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="Yo",
            body="Hey",
        )
        db.session.add(msg)
        db.session.commit()

        assert "Yo" in repr(msg)
        assert str(sender.id) in repr(msg)
        assert str(receiver.id) in repr(msg)


class TestNoteModel:
    """Test the Note model."""

    def test_create_note(self, db):
        """Create a note for an agent."""
        from models import Agent, Note
        from datetime import datetime, timezone

        agent = Agent(name="NoteTaker", role="note-taker")
        db.session.add(agent)
        db.session.flush()

        note = Note(
            agent_id=agent.id,
            title="My Note",
            body="This is a useful note.",
            tags=["important", "idea"],
            pinned=True,
        )
        db.session.add(note)
        db.session.commit()

        assert note.id is not None
        assert note.agent_id == agent.id
        assert note.title == "My Note"
        assert note.body == "This is a useful note."
        assert note.tags == ["important", "idea"]
        assert note.pinned is True
        assert isinstance(note.created_at, datetime)
        assert isinstance(note.updated_at, datetime)

    def test_note_defaults(self, db):
        """Note defaults to unpinned with empty tags."""
        from models import Agent, Note

        agent = Agent(name="DefaultNoteTaker", role="note-taker")
        db.session.add(agent)
        db.session.flush()

        note = Note(
            agent_id=agent.id,
            title="Default Note",
            body="Default body.",
        )
        db.session.add(note)
        db.session.commit()

        assert note.pinned is False
        assert note.tags == []

    def test_note_relationship(self, db):
        """Note belongs to an agent."""
        from models import Agent, Note

        agent = Agent(name="NoteOwner", role="owner")
        db.session.add(agent)
        db.session.flush()

        note = Note(
            agent_id=agent.id,
            title="Owned Note",
            body="Body",
        )
        db.session.add(note)
        db.session.commit()

        assert note.agent.name == "NoteOwner"
        notes_list = agent.notes.all()
        assert len(notes_list) == 1
        assert notes_list[0].title == "Owned Note"

    def test_note_repr(self, db):
        """Note has useful __repr__."""
        from models import Agent, Note

        agent = Agent(name="ReprOwner", role="owner")
        db.session.add(agent)
        db.session.flush()

        note = Note(
            agent_id=agent.id,
            title="Repr Note",
            body="Body",
        )
        db.session.add(note)
        db.session.commit()

        assert "Repr Note" in repr(note)
