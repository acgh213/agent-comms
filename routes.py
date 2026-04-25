"""Routes for the agent comms dashboard."""

from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
)
from sqlalchemy import desc, func

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_models():
    """Lazy-import models to avoid circular imports at module level."""
    from models import Agent, Conversation, Message, Note

    return Agent, Conversation, Message, Note


def _human_time(dt):
    """Return a friendly relative-time string for a datetime (or None)."""
    if dt is None:
        return "never"
    now = datetime.now(timezone.utc)
    # SQLite stores datetimes without tzinfo, so if dt is naive, make now naive too
    if dt.tzinfo is None:
        now = now.replace(tzinfo=None)
    diff = now - dt
    secs = int(diff.total_seconds())
    if secs < 10:
        return "just now"
    if secs < 60:
        return f"{secs}s ago"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Dashboard overview
# ---------------------------------------------------------------------------


@dashboard_bp.route("/")
def index():
    Agent, Conversation, Message, Note = _get_models()

    agents = Agent.query.order_by(Agent.name).all()
    online_count = Agent.query.filter(Agent.status == "online").count()
    unread_count = Message.query.filter(
        Message.read_at.is_(None), Message.status == "sent"
    ).count()

    # Active = conversations with at least one message, ordered by last update
    active_convs = (
        Conversation.query.join(Message)
        .order_by(desc(Conversation.updated_at))
        .distinct()
        .all()
    )

    recent_messages = (
        Message.query.order_by(desc(Message.created_at)).limit(10).all()
    )

    stats = {
        "total_agents": len(agents),
        "online_agents": online_count,
        "unread_messages": unread_count,
        "active_conversations": len(active_convs),
    }

    return render_template(
        "dashboard.html",
        agents=agents,
        recent_messages=recent_messages,
        conversations=active_convs,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Agent detail
# ---------------------------------------------------------------------------


@dashboard_bp.route("/agents/")
def agents_list():
    Agent, _, _, _ = _get_models()
    agents = Agent.query.order_by(Agent.name).all()
    return render_template("messages.html", messages=[])


@dashboard_bp.route("/agent/<int:agent_id>")
def agent_detail(agent_id):
    Agent, _, Message, Note = _get_models()

    agent = Agent.query.get_or_404(agent_id)
    all_agents = Agent.query.filter(Agent.id != agent_id).order_by(Agent.name).all()

    # Messages where this agent is sender or receiver
    messages = (
        Message.query.filter(
            (Message.from_agent_id == agent_id)
            | (Message.to_agent_id == agent_id)
        )
        .order_by(desc(Message.created_at))
        .limit(50)
        .all()
    )

    notes = Note.query.filter_by(agent_id=agent_id).order_by(desc(Note.created_at)).all()

    return render_template(
        "agent.html",
        agent=agent,
        all_agents=all_agents,
        messages=messages,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Conversation detail
# ---------------------------------------------------------------------------


@dashboard_bp.route("/conversations/")
def conversations_list():
    Agent, Conversation, Message, _ = _get_models()
    convs = (
        Conversation.query.order_by(desc(Conversation.updated_at)).all()
    )
    return render_template("messages.html", messages=[])


@dashboard_bp.route("/conversation/<int:conv_id>")
def conversation_detail(conv_id):
    Agent, Conversation, Message, _ = _get_models()

    conv = Conversation.query.get_or_404(conv_id)
    messages = (
        Message.query.filter_by(conversation_id=conv_id)
        .order_by(Message.created_at)
        .all()
    )

    return render_template(
        "conversation.html",
        conversation=conv,
        messages=messages,
    )


# ---------------------------------------------------------------------------
# Messages queue
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------


@dashboard_bp.route("/compose", methods=["GET", "POST"])
def compose():
    """GET — render compose form. POST — handle form submission (fallback)."""
    Agent, _, Message, _ = _get_models()
    agents = Agent.query.order_by(Agent.name).all()

    if request.method == "POST":
        from_agent_id = request.form.get("from_agent_id", type=int)
        to_agent_id = request.form.get("to_agent_id", type=int)
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()
        msg_type = request.form.get("type", "notification")
        priority = request.form.get("priority", "normal")

        if not all([from_agent_id, to_agent_id]):
            return render_template("compose.html", agents=agents, error="From and To agents are required.")

        sender = Agent.query.get(from_agent_id)
        receiver = Agent.query.get(to_agent_id)
        if not sender or not receiver:
            return render_template("compose.html", agents=agents, error="Agent not found.")

        from bus import MessageBus

        bus = MessageBus(__import__("app").db)
        conv = bus.create_conversation(
            f"{sender.name} ↔ {receiver.name}",
            [from_agent_id, to_agent_id],
        )
        msg = bus.send(
            from_agent=from_agent_id,
            to_agent=to_agent_id,
            type=msg_type,
            subject=subject or "(no subject)",
            body=body,
            priority=priority,
            conversation_id=conv.id,
        )
        from urllib.parse import urlencode

        return redirect(f"/conversation/{conv.id}")

    from_agent_id = request.args.get("from", type=int)
    return render_template("compose.html", agents=agents, from_agent_id=from_agent_id)


@dashboard_bp.route("/messages/")
def messages_list():
    Agent, _, Message, _ = _get_models()
    messages = (
        Message.query.order_by(desc(Message.created_at)).limit(100).all()
    )
    return render_template("messages.html", messages=messages)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@dashboard_bp.route("/api/messages/send", methods=["POST"])
def send_message_api():
    Agent, _, Message, _ = _get_models()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "error": "Invalid JSON"}), 400

    from_agent_id = data.get("from_agent_id")
    to_agent_id = data.get("to_agent_id")
    subject = data.get("subject", "")
    body = data.get("body", "")
    msg_type = data.get("type", "text")
    priority = data.get("priority", "normal")
    conversation_id = data.get("conversation_id")

    if not all([from_agent_id, to_agent_id]):
        return jsonify({"status": "error", "error": "from_agent_id and to_agent_id required"}), 400

    sender = Agent.query.get(from_agent_id)
    receiver = Agent.query.get(to_agent_id)
    if not sender or not receiver:
        return jsonify({"status": "error", "error": "Agent not found"}), 404

    # Auto-create conversation if not provided
    if not conversation_id:
        from bus import MessageBus

        bus = MessageBus(__import__("app").db)
        conv = bus.create_conversation(
            f"{sender.name} ↔ {receiver.name}",
            [from_agent_id, to_agent_id],
        )
        conversation_id = conv.id
        msg = bus.send(
            from_agent=from_agent_id,
            to_agent=to_agent_id,
            type=msg_type,
            subject=subject,
            body=body,
            priority=priority,
            conversation_id=conversation_id,
        )
    else:
        from models import Conversation

        conv = Conversation.query.get(conversation_id)
        if not conv:
            return jsonify({"status": "error", "error": "Conversation not found"}), 404

        msg = Message(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            conversation_id=conversation_id,
            type=msg_type,
            priority=priority,
            status="sent",
            subject=subject,
            body=body,
        )
        from app import db

        db.session.add(msg)
        db.session.commit()

        conv.updated_at = datetime.now(timezone.utc)
        db.session.commit()

    return jsonify(
        {
            "status": "ok",
            "message": {
                "id": msg.id,
                "sender_name": sender.name,
                "sender_color": sender.avatar_color,
                "receiver_name": receiver.name,
                "receiver_color": receiver.avatar_color,
                "subject": msg.subject,
                "body": msg.body,
                "priority": msg.priority,
                "conversation_id": msg.conversation_id,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            },
        }
    )


@dashboard_bp.route("/api/messages/<int:msg_id>/read", methods=["POST"])
def mark_read_api(msg_id):
    Agent, _, Message, _ = _get_models()
    msg = Message.query.get_or_404(msg_id)
    msg.read_at = datetime.now(timezone.utc)
    from app import db

    db.session.commit()
    return jsonify({"status": "ok", "message_id": msg_id})


@dashboard_bp.route("/api/messages/<int:msg_id>/acknowledge", methods=["POST"])
def acknowledge_api(msg_id):
    Agent, _, Message, _ = _get_models()
    msg = Message.query.get_or_404(msg_id)
    msg.acknowledged_at = datetime.now(timezone.utc)
    from app import db

    db.session.commit()
    return jsonify({"status": "ok", "message_id": msg_id})


# ---------------------------------------------------------------------------
# Template globals
# ---------------------------------------------------------------------------


def register_template_globals(app):
    """Register filters and context processors used by the templates."""

    @app.template_filter("timesince")
    def timesince_filter(dt):
        return _human_time(dt)

    @app.context_processor
    def inject_globals():
        return {}
