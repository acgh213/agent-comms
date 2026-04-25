"""REST API Blueprint for Agent Comms."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app import db
from bus import MessageBus
from models import (
    Agent,
    Conversation,
    Message,
    Note,
    conversation_participants as cp_table,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")
bus = MessageBus(db)

# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def serialize_agent(agent):
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "personality": agent.personality,
        "capabilities": agent.capabilities,
        "status": agent.status,
        "avatar_color": agent.avatar_color,
        "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
        "created_at": agent.created_at.isoformat(),
    }


def serialize_message(msg):
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
        "attachments": msg.attachments,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
        "acknowledged_at": (
            msg.acknowledged_at.isoformat() if msg.acknowledged_at else None
        ),
    }


def serialize_conversation(conv):
    return {
        "id": conv.id,
        "title": conv.title,
        "participants": [p.id for p in conv.participants],
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


def serialize_note(note):
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


def _find_or_create_direct_conversation(agent1_id, agent2_id):
    """Find an existing *direct* (exactly 2 participant) conversation between
    two agents, or create one."""
    # Get conversation IDs containing agent1
    a1_convs = set(
        row[0]
        for row in db.session.query(cp_table.c.conversation_id).filter(
            cp_table.c.agent_id == agent1_id
        ).all()
    )
    # Get conversation IDs containing agent2
    a2_convs = set(
        row[0]
        for row in db.session.query(cp_table.c.conversation_id).filter(
            cp_table.c.agent_id == agent2_id
        ).all()
    )

    common = a1_convs & a2_convs
    for conv_id in common:
        conv = db.session.get(Conversation, conv_id)
        if conv and len(conv.participants) == 2:
            return conv

    # Create new direct conversation
    a1 = db.session.get(Agent, agent1_id)
    a2 = db.session.get(Agent, agent2_id)
    if not a1 or not a2:
        return None
    conv = Conversation(title=f"{a1.name} & {a2.name}", participants=[a1, a2])
    db.session.add(conv)
    db.session.commit()
    return conv


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@api_bp.route("/agents", methods=["GET"])
def list_agents():
    """List all agents, ordered by name."""
    agents = Agent.query.order_by(Agent.name).all()
    return jsonify([serialize_agent(a) for a in agents])


@api_bp.route("/agents/<int:agent_id>", methods=["GET"])
def get_agent(agent_id):
    """Agent detail including recent messages (last 20)."""
    agent = db.session.get(Agent, agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    data = serialize_agent(agent)
    recent = (
        Message.query.filter(
            (Message.from_agent_id == agent_id) | (Message.to_agent_id == agent_id)
        )
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )
    data["recent_messages"] = [serialize_message(m) for m in recent]
    return jsonify(data)


@api_bp.route("/agents/<int:agent_id>/status", methods=["PUT"])
def update_agent_status(agent_id):
    """Update an agent's status."""
    agent = db.session.get(Agent, agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    body = request.get_json()
    if not body or "status" not in body:
        return jsonify({"error": "status field required"}), 400

    agent.status = body["status"]
    agent.last_seen = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(serialize_agent(agent))


# ---------------------------------------------------------------------------
# Message endpoints
# ---------------------------------------------------------------------------


@api_bp.route("/messages", methods=["GET"])
def list_messages():
    """List messages, filterable by agent_id, type, status."""
    query = Message.query

    agent_id = request.args.get("agent_id")
    msg_type = request.args.get("type")
    status = request.args.get("status")

    if agent_id:
        aid = int(agent_id)
        query = query.filter(
            (Message.from_agent_id == aid) | (Message.to_agent_id == aid)
        )
    if msg_type:
        query = query.filter(Message.type == msg_type)
    if status:
        query = query.filter(Message.status == status)

    messages = query.order_by(Message.created_at.desc()).all()
    return jsonify([serialize_message(m) for m in messages])


@api_bp.route("/messages", methods=["POST"])
def send_message():
    """Send a message from one agent to another. Creates or reuses a direct
    conversation between the two agents."""
    body = request.get_json()
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    required = ["from_agent_id", "to_agent_id", "type", "subject", "body"]
    for field in required:
        if field not in body:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    from_id = int(body["from_agent_id"])
    to_id = int(body["to_agent_id"])

    conv = _find_or_create_direct_conversation(from_id, to_id)
    if conv is None:
        return jsonify({"error": "One or both agents not found"}), 404

    msg = bus.send(
        from_agent=from_id,
        to_agent=to_id,
        type=body["type"],
        subject=body["subject"],
        body=body["body"],
        priority=body.get("priority", "normal"),
        conversation_id=conv.id,
    )
    return jsonify(serialize_message(msg)), 201


@api_bp.route("/messages/<int:message_id>/read", methods=["PUT"])
def mark_message_read(message_id):
    """Mark a message as read."""
    msg = db.session.get(Message, message_id)
    if not msg:
        return jsonify({"error": "Message not found"}), 404
    bus.mark_read(msg)
    return jsonify(serialize_message(msg))


@api_bp.route("/messages/<int:message_id>/acknowledge", methods=["PUT"])
def acknowledge_message(message_id):
    """Mark a message as acknowledged."""
    msg = db.session.get(Message, message_id)
    if not msg:
        return jsonify({"error": "Message not found"}), 404
    bus.mark_acknowledged(msg)
    return jsonify(serialize_message(msg))


# ---------------------------------------------------------------------------
# Conversation endpoints
# ---------------------------------------------------------------------------


@api_bp.route("/conversations", methods=["GET"])
def list_conversations():
    """List all conversations, most recently updated first."""
    convs = Conversation.query.order_by(Conversation.updated_at.desc()).all()
    return jsonify([serialize_conversation(c) for c in convs])


@api_bp.route("/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation with participants."""
    body = request.get_json()
    if not body or "title" not in body:
        return jsonify({"error": "title field required"}), 400

    participants = body.get("participants", [])
    conv = bus.create_conversation(title=body["title"], participants=participants)
    return jsonify(serialize_conversation(conv)), 201


@api_bp.route("/conversations/<int:conversation_id>/messages", methods=["GET"])
def get_conversation_messages(conversation_id):
    """Get all messages in a conversation."""
    conv = db.session.get(Conversation, conversation_id)
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    messages = bus.get_conversation(conversation_id)
    return jsonify([serialize_message(m) for m in messages])


# ---------------------------------------------------------------------------
# Note endpoints
# ---------------------------------------------------------------------------


@api_bp.route("/notes", methods=["GET"])
def list_notes():
    """List notes, filterable by agent_id and pinned."""
    query = Note.query

    agent_id = request.args.get("agent_id")
    pinned = request.args.get("pinned")

    if agent_id:
        query = query.filter(Note.agent_id == int(agent_id))
    if pinned is not None:
        query = query.filter(Note.pinned == (pinned.lower() == "true"))

    notes = query.order_by(Note.updated_at.desc()).all()
    return jsonify([serialize_note(n) for n in notes])


@api_bp.route("/notes", methods=["POST"])
def create_note():
    """Create a new note for an agent."""
    body = request.get_json()
    if not body:
        return jsonify({"error": "JSON body required"}), 400
    if "agent_id" not in body:
        return jsonify({"error": "agent_id field required"}), 400
    if "title" not in body:
        return jsonify({"error": "title field required"}), 400

    note = Note(
        agent_id=int(body["agent_id"]),
        title=body["title"],
        body=body.get("body"),
        tags=body.get("tags", []),
        pinned=body.get("pinned", False),
    )
    db.session.add(note)
    db.session.commit()
    return jsonify(serialize_note(note)), 201


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------


@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """Dashboard statistics."""
    return jsonify(
        {
            "total_agents": Agent.query.count(),
            "unread_messages": Message.query.filter(Message.read_at.is_(None)).count(),
            "active_conversations": Conversation.query.count(),
        }
    )
