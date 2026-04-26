"""Database models for Agent Comms."""
from datetime import datetime, timezone

from app import db

# ---------------------------------------------------------------------------
# Association table: conversation <-> agent (many-to-many)
# ---------------------------------------------------------------------------

conversation_participants = db.Table(
    "conversation_participants",
    db.Column(
        "conversation_id",
        db.Integer,
        db.ForeignKey("conversation.id"),
        primary_key=True,
    ),
    db.Column(
        "agent_id",
        db.Integer,
        db.ForeignKey("agent.id"),
        primary_key=True,
    ),
)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent(db.Model):
    __tablename__ = "agent"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    role = db.Column(db.String(64), nullable=False, default="assistant")
    personality = db.Column(db.Text, nullable=True)
    capabilities = db.Column(db.JSON, nullable=False, default=list)
    status = db.Column(
        db.String(32), nullable=False, default="offline"
    )
    avatar_color = db.Column(db.String(7), nullable=True)
    preferred_model = db.Column(db.String(256), nullable=True)
    last_seen = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    messages_sent = db.relationship(
        "Message",
        foreign_keys="Message.from_agent_id",
        back_populates="sender",
        lazy="dynamic",
    )
    messages_received = db.relationship(
        "Message",
        foreign_keys="Message.to_agent_id",
        back_populates="receiver",
        lazy="dynamic",
    )
    notes = db.relationship("Note", back_populates="agent", lazy="dynamic")
    conversations = db.relationship(
        "Conversation",
        secondary=conversation_participants,
        back_populates="participants",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Agent {self.name} ({self.role})>"


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class Conversation(db.Model):
    __tablename__ = "conversation"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False, default="Untitled")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    participants = db.relationship(
        "Agent",
        secondary=conversation_participants,
        back_populates="conversations",
        lazy="select",
    )
    messages = db.relationship(
        "Message",
        back_populates="conversation",
        lazy="dynamic",
        order_by="Message.created_at",
    )

    def __repr__(self):
        return f"<Conversation {self.id}: {self.title}>"


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    from_agent_id = db.Column(
        db.Integer, db.ForeignKey("agent.id"), nullable=False
    )
    to_agent_id = db.Column(
        db.Integer, db.ForeignKey("agent.id"), nullable=False
    )
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversation.id"), nullable=False
    )
    type = db.Column(db.String(32), nullable=False, default="text")
    priority = db.Column(
        db.String(16), nullable=False, default="normal"
    )
    status = db.Column(db.String(32), nullable=False, default="sent")
    subject = db.Column(db.String(256), nullable=True)
    body = db.Column(db.Text, nullable=True)
    attachments = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    acknowledged_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    sender = db.relationship(
        "Agent",
        foreign_keys=[from_agent_id],
        back_populates="messages_sent",
    )
    receiver = db.relationship(
        "Agent",
        foreign_keys=[to_agent_id],
        back_populates="messages_received",
    )
    conversation = db.relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self):
        return (
            f"<Message {self.id}: {self.subject or '(no subject)'} "
            f"{self.from_agent_id}->{self.to_agent_id}>"
        )


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------

class Note(db.Model):
    __tablename__ = "note"

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(
        db.Integer, db.ForeignKey("agent.id"), nullable=False
    )
    title = db.Column(db.String(256), nullable=False, default="Untitled")
    body = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, nullable=False, default=list)
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    agent = db.relationship("Agent", back_populates="notes")

    def __repr__(self):
        return f"<Note {self.id}: {self.title}>"
