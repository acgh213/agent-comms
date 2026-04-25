"""Tests for the message bus."""
from datetime import datetime, timezone


class TestMessageBus:
    """Test the MessageBus class."""

    def test_send_message(self, app, db):
        """Send a message between agents in a conversation."""
        from models import Agent, Conversation
        from bus import MessageBus

        bus = MessageBus(db)

        sender = Agent(name="Sender", role="sender", status="online")
        receiver = Agent(name="Receiver", role="receiver", status="online")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Test Chat", participants=[sender, receiver])
        db.session.add(conv)
        db.session.commit()

        msg = bus.send(
            from_agent=sender.id,
            to_agent=receiver.id,
            type="text",
            subject="Hello",
            body="Hi there!",
            priority="high",
            conversation_id=conv.id,
        )

        assert msg is not None
        assert msg.from_agent_id == sender.id
        assert msg.to_agent_id == receiver.id
        assert msg.conversation_id == conv.id
        assert msg.type == "text"
        assert msg.subject == "Hello"
        assert msg.body == "Hi there!"
        assert msg.priority == "high"
        assert msg.status == "sent"
        assert msg.created_at is not None

    def test_send_message_defaults(self, app, db):
        """Send with minimal fields uses sensible defaults."""
        from models import Agent, Conversation
        from bus import MessageBus

        bus = MessageBus(db)

        sender = Agent(name="S1", role="sender")
        receiver = Agent(name="R1", role="receiver")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Chat", participants=[sender, receiver])
        db.session.add(conv)
        db.session.commit()

        msg = bus.send(
            from_agent=sender.id,
            to_agent=receiver.id,
            type="text",
            subject="Hi",
            body="Test",
            conversation_id=conv.id,
        )

        assert msg.priority == "normal"
        assert msg.status == "sent"

    def test_get_unread(self, app, db):
        """Get all unread messages for an agent."""
        from models import Agent, Conversation
        from bus import MessageBus

        bus = MessageBus(db)

        sender = Agent(name="UnreadSender", role="sender")
        receiver = Agent(name="UnreadReceiver", role="receiver")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Unread Chat", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        bus.send(
            from_agent=sender.id,
            to_agent=receiver.id,
            type="text",
            subject="Msg 1",
            body="Body 1",
            conversation_id=conv.id,
        )
        bus.send(
            from_agent=sender.id,
            to_agent=receiver.id,
            type="text",
            subject="Msg 2",
            body="Body 2",
            conversation_id=conv.id,
        )

        # Mark first message as read
        all_msgs = bus.get_conversation(conv.id)
        bus.mark_read(all_msgs[0])

        unread = bus.get_unread(receiver.id)
        assert len(unread) == 1
        assert unread[0].subject == "Msg 2"

    def test_get_unread_no_messages(self, app, db):
        """No unread messages returns empty list."""
        from models import Agent
        from bus import MessageBus

        bus = MessageBus(db)

        agent = Agent(name="Lonely", role="loner")
        db.session.add(agent)
        db.session.commit()

        unread = bus.get_unread(agent.id)
        assert unread == []

    def test_get_conversation(self, app, db):
        """Get messages in a conversation ordered by creation time."""
        from models import Agent, Conversation
        from bus import MessageBus

        bus = MessageBus(db)

        a1 = Agent(name="A1", role="one")
        a2 = Agent(name="A2", role="two")
        db.session.add_all([a1, a2])
        db.session.flush()

        conv = Conversation(title="Ordered Chat", participants=[a1, a2])
        db.session.add(conv)
        db.session.commit()

        bus.send(
            from_agent=a1.id,
            to_agent=a2.id,
            type="text",
            subject="First",
            body="First message",
            conversation_id=conv.id,
        )
        bus.send(
            from_agent=a2.id,
            to_agent=a1.id,
            type="text",
            subject="Second",
            body="Second message",
            conversation_id=conv.id,
        )

        msgs = bus.get_conversation(conv.id)
        assert len(msgs) == 2
        assert msgs[0].subject == "First"
        assert msgs[1].subject == "Second"

    def test_get_conversation_empty(self, app, db):
        """Empty conversation returns empty list."""
        from models import Agent, Conversation
        from bus import MessageBus

        bus = MessageBus(db)

        a1 = Agent(name="C1", role="one")
        a2 = Agent(name="C2", role="two")
        db.session.add_all([a1, a2])
        db.session.flush()

        conv = Conversation(title="Empty Chat", participants=[a1, a2])
        db.session.add(conv)
        db.session.commit()

        msgs = bus.get_conversation(conv.id)
        assert msgs == []

    def test_mark_read(self, app, db):
        """Mark a message as read."""
        from models import Agent, Conversation
        from bus import MessageBus

        bus = MessageBus(db)

        a1 = Agent(name="ReadSender", role="sender")
        a2 = Agent(name="ReadReceiver", role="receiver")
        db.session.add_all([a1, a2])
        db.session.flush()

        conv = Conversation(title="Read Chat", participants=[a1, a2])
        db.session.add(conv)
        db.session.commit()

        msg = bus.send(
            from_agent=a1.id,
            to_agent=a2.id,
            type="text",
            subject="Read Me",
            body="Please read me",
            conversation_id=conv.id,
        )

        assert msg.read_at is None
        bus.mark_read(msg)
        assert msg.read_at is not None
        assert isinstance(msg.read_at, datetime)

    def test_mark_acknowledged(self, app, db):
        """Mark a message as acknowledged."""
        from models import Agent, Conversation
        from bus import MessageBus

        bus = MessageBus(db)

        a1 = Agent(name="AckSender", role="sender")
        a2 = Agent(name="AckReceiver", role="receiver")
        db.session.add_all([a1, a2])
        db.session.flush()

        conv = Conversation(title="Ack Chat", participants=[a1, a2])
        db.session.add(conv)
        db.session.commit()

        msg = bus.send(
            from_agent=a1.id,
            to_agent=a2.id,
            type="text",
            subject="Ack Me",
            body="Please acknowledge",
            conversation_id=conv.id,
        )

        assert msg.acknowledged_at is None
        bus.mark_acknowledged(msg)
        assert msg.acknowledged_at is not None
        assert isinstance(msg.acknowledged_at, datetime)

    def test_create_conversation(self, app, db):
        """Create a conversation with participants."""
        from models import Agent
        from bus import MessageBus

        bus = MessageBus(db)

        a1 = Agent(name="P1", role="participant")
        a2 = Agent(name="P2", role="participant")
        a3 = Agent(name="P3", role="participant")
        db.session.add_all([a1, a2, a3])
        db.session.commit()

        conv = bus.create_conversation(
            title="New Planning Session",
            participants=[a1.id, a2.id, a3.id],
        )

        assert conv.id is not None
        assert conv.title == "New Planning Session"
        assert len(conv.participants) == 3
        participant_ids = {p.id for p in conv.participants}
        assert participant_ids == {a1.id, a2.id, a3.id}

    def test_create_conversation_no_participants(self, app, db):
        """Create a conversation without participants."""
        from bus import MessageBus

        bus = MessageBus(db)

        conv = bus.create_conversation(title="Empty Room", participants=[])
        assert conv.id is not None
        assert conv.title == "Empty Room"
        assert conv.participants == []
