"""Message bus — routing and message management for agents."""
from datetime import datetime, timezone

from models import Agent, Conversation, Message


class MessageBus:
    """Central message bus for agent-to-agent communication."""

    def __init__(self, db):
        self.db = db

    def send(
        self,
        from_agent,
        to_agent,
        type,
        subject,
        body,
        priority="normal",
        conversation_id=None,
    ):
        """Send a message from one agent to another.

        Returns the created Message instance.
        """
        msg = Message(
            from_agent_id=from_agent,
            to_agent_id=to_agent,
            conversation_id=conversation_id,
            type=type,
            priority=priority,
            status="sent",
            subject=subject,
            body=body,
        )
        self.db.session.add(msg)
        self.db.session.commit()
        return msg

    def get_unread(self, agent):
        """Get all unread messages for an agent (read_at is None)."""
        return (
            Message.query.filter_by(to_agent_id=agent, read_at=None)
            .order_by(Message.created_at.asc())
            .all()
        )

    def get_conversation(self, conversation_id):
        """Get all messages in a conversation, ordered by creation time."""
        return (
            Message.query.filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    def mark_read(self, message):
        """Mark a message as read."""
        message.read_at = datetime.now(timezone.utc)
        self.db.session.commit()

    def mark_acknowledged(self, message):
        """Mark a message as acknowledged."""
        message.acknowledged_at = datetime.now(timezone.utc)
        self.db.session.commit()

    def create_conversation(self, title, participants):
        """Create a new conversation with the given list of agent IDs.

        Returns the created Conversation instance.
        """
        agent_objs = Agent.query.filter(Agent.id.in_(participants)).all()
        conv = Conversation(title=title, participants=agent_objs)
        self.db.session.add(conv)
        self.db.session.commit()
        return conv
