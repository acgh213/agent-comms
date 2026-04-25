"""Hermes integration tool — agent-to-agent communication via the message bus.

This module provides a Pythonic interface for Hermes agents to communicate
using the Agent Comms message bus. Each function creates a Flask app context,
performs the operation through the MessageBus, and returns clean dicts.

Usage:
    from hermes_tool import send_message, check_messages, reply_to

    send_message("agent-bob", "Status Check", "What's your status?")
    msgs = check_messages("agent-alice")
    reply_to(msgs[0]["id"], "I'm online and ready.")
"""
from datetime import datetime, timezone

from app import create_app, db
from bus import MessageBus
from models import Agent, Conversation, Message, Note, conversation_participants

# ---------------------------------------------------------------------------
# Module-level state (lazy-initialised, overridable via configure())
# ---------------------------------------------------------------------------

_app = None
_bus = None


def configure(app=None):
    """Override the internal Flask app (used by tests to share a test app).

    If *app* is ``None`` (default), the module will create its own app on
        first use.
    """
    global _app, _bus
    if app is not None:
        _app = app
        _bus = MessageBus(db)


def _ensure():
    """Lazy init + push a fresh app context; return the context manager."""
    global _app, _bus
    if _app is None:
        _app = create_app()
    if _bus is None:
        _bus = MessageBus(db)
    return _app.app_context()


# ---------------------------------------------------------------------------
# Serialisation helpers (produce plain dicts, not model objects)
# ---------------------------------------------------------------------------


def _serialize_message(msg):
    if msg is None:
        return None
    return {
        "id": msg.id,
        "from_agent_id": msg.from_agent_id,
        "to_agent_id": msg.to_agent_id,
        "conversation_id": msg.conversation_id,
        "type": msg.type,
        "priority": msg.priority,
        "status": msg.status,
        "subject": msg.subject,
        "body": msg.body,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
        "acknowledged_at": msg.acknowledged_at.isoformat()
        if msg.acknowledged_at
        else None,
    }


def _serialize_conversation(conv):
    if conv is None:
        return None
    return {
        "id": conv.id,
        "title": conv.title,
        "participants": [p.id for p in conv.participants],
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


def _serialize_note(note):
    if note is None:
        return None
    return {
        "id": note.id,
        "agent_id": note.agent_id,
        "title": note.title,
        "body": note.body,
        "tags": note.tags,
        "pinned": note.pinned,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_agent_by_name(name):
    """Return the Agent for *name*, or ``None``."""
    return Agent.query.filter_by(name=name).first()


def _get_or_create_agent(name, role="assistant"):
    """Return an existing Agent by *name*, or create one."""
    agent = _find_agent_by_name(name)
    if agent is None:
        agent = Agent(name=name, role=role, status="online")
        db.session.add(agent)
        db.session.commit()
    return agent


def _find_direct_conversation(agent1_id, agent2_id):
    """Return an existing direct (exactly 2-participant) conversation, or
    ``None``."""
    a1_convs = set(
        row[0]
        for row in db.session.query(conversation_participants.c.conversation_id)
        .filter(conversation_participants.c.agent_id == agent1_id)
        .all()
    )
    a2_convs = set(
        row[0]
        for row in db.session.query(conversation_participants.c.conversation_id)
        .filter(conversation_participants.c.agent_id == agent2_id)
        .all()
    )
    for conv_id in a1_convs & a2_convs:
        conv = db.session.get(Conversation, conv_id)
        if conv and len(conv.participants) == 2:
            return conv
    return None


def _create_direct_conversation(agent1_id, agent2_id):
    """Create a new direct conversation between two agents."""
    a1 = db.session.get(Agent, agent1_id)
    a2 = db.session.get(Agent, agent2_id)
    if not a1 or not a2:
        return None
    conv = Conversation(title=f"{a1.name} & {a2.name}", participants=[a1, a2])
    db.session.add(conv)
    db.session.commit()
    return conv


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_message(
    to_name, subject, body, msg_type="request", priority="normal"
):
    """Send a message to another agent by name.

    Parameters
    ----------
    to_name : str
        Name of the receiving agent (created if it doesn't exist — see
        *auto-register*).
    subject : str
        Message subject line.
    body : str
        Message body content.
    msg_type : str, optional
        Message type (default ``"request"``).
    priority : str, optional
        Priority level — ``"normal"``, ``"high"``, ``"low"`` (default ``"normal"``).

    Returns
    -------
    dict
        The created message as a plain dict, or a dict with an ``"error"`` key
        on failure.
    """
    with _ensure():
        try:
            agent_from = _get_or_create_agent("hermes")
            agent_to = _get_or_create_agent(to_name)

            conv = _find_direct_conversation(agent_from.id, agent_to.id)
            if conv is None:
                conv = _create_direct_conversation(
                    agent_from.id, agent_to.id
                )
            if conv is None:
                return {"error": "Could not create conversation"}

            msg = _bus.send(
                from_agent=agent_from.id,
                to_agent=agent_to.id,
                type=msg_type,
                subject=subject,
                body=body,
                priority=priority,
                conversation_id=conv.id,
            )
            return _serialize_message(msg)
        except Exception as exc:
            return {"error": str(exc)}


def check_messages(agent_name=None):
    """Check unread messages.

    If *agent_name* is given, only return messages for that agent.
    If ``None``, return all unread messages across every agent.

    Returns
    -------
    list[dict]
    """
    with _ensure():
        try:
            if agent_name is not None:
                agent = _find_agent_by_name(agent_name)
                if agent is None:
                    return []
                msgs = _bus.get_unread(agent.id)
            else:
                msgs = (
                    Message.query.filter(Message.read_at.is_(None))
                    .order_by(Message.created_at.asc())
                    .all()
                )
            return [_serialize_message(m) for m in msgs]
        except Exception as exc:
            return [{"error": str(exc)}]


def read_message(message_id):
    """Mark a message as read.

    Parameters
    ----------
    message_id : int

    Returns
    -------
    dict
        The updated message, or ``{"error": ...}``.
    """
    with _ensure():
        try:
            msg = db.session.get(Message, message_id)
            if msg is None:
                return {"error": "Message not found"}
            _bus.mark_read(msg)
            return _serialize_message(msg)
        except Exception as exc:
            return {"error": str(exc)}


def acknowledge_message(message_id):
    """Mark a message as acknowledged.

    Parameters
    ----------
    message_id : int

    Returns
    -------
    dict
        The updated message, or ``{"error": ...}``.
    """
    with _ensure():
        try:
            msg = db.session.get(Message, message_id)
            if msg is None:
                return {"error": "Message not found"}
            _bus.mark_acknowledged(msg)
            return _serialize_message(msg)
        except Exception as exc:
            return {"error": str(exc)}


def leave_note(title, body, tags=None, pinned=False):
    """Leave a note for other agents (associated with the ``"hermes"`` agent).

    Parameters
    ----------
    title : str
    body : str
    tags : list[str], optional
    pinned : bool, optional

    Returns
    -------
    dict
        The created note, or ``{"error": ...}``.
    """
    with _ensure():
        try:
            agent = _get_or_create_agent("hermes")
            note = Note(
                agent_id=agent.id,
                title=title,
                body=body,
                tags=tags or [],
                pinned=pinned,
            )
            db.session.add(note)
            db.session.commit()
            return _serialize_note(note)
        except Exception as exc:
            return {"error": str(exc)}


def get_conversations(agent_name=None):
    """Get recent conversations.

    If *agent_name* is given, only return conversations that agent
    participates in.

    Returns
    -------
    list[dict]
    """
    with _ensure():
        try:
            query = Conversation.query.order_by(
                Conversation.updated_at.desc()
            )
            if agent_name is not None:
                agent = _find_agent_by_name(agent_name)
                if agent is None:
                    return []
                query = query.filter(
                    Conversation.participants.any(id=agent.id)
                )
            convs = query.all()
            return [_serialize_conversation(c) for c in convs]
        except Exception as exc:
            return [{"error": str(exc)}]


def reply_to(message_id, body, msg_type="response", priority="normal"):
    """Reply to a message, creating a conversation thread.

    The reply is sent in the same conversation as the original message, with
    the sender/receiver roles swapped.

    Parameters
    ----------
    message_id : int
        ID of the message to reply to.
    body : str
        Reply body text.
    msg_type : str, optional
        Type for the reply (default ``"response"``).
    priority : str, optional
        Priority for the reply (default ``"normal"``).

    Returns
    -------
    dict
        The created reply message, or ``{"error": ...}``.
    """
    with _ensure():
        try:
            original = db.session.get(Message, message_id)
            if original is None:
                return {"error": "Original message not found"}

            agent_from = db.session.get(Agent, original.to_agent_id)
            agent_to = db.session.get(Agent, original.from_agent_id)
            if agent_from is None or agent_to is None:
                return {"error": "Sender or recipient agent not found"}

            reply = _bus.send(
                from_agent=agent_from.id,
                to_agent=agent_to.id,
                type=msg_type,
                subject=f"Re: {original.subject or '(no subject)'}",
                body=body,
                priority=priority,
                conversation_id=original.conversation_id,
            )
            return _serialize_message(reply)
        except Exception as exc:
            return {"error": str(exc)}
