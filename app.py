"""Agent Comms — Flask application factory."""

import logging
import os
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
socketio = SocketIO()

log = logging.getLogger("agent-comms")

# Absolute DB path — never relative, never fragile
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "agent_comms.db")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Force absolute DB path — this is why it keeps collapsing
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    db.init_app(app)
    socketio.init_app(app, async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "eventlet"))

    # Import models + create tables inside app context
    with app.app_context():
        import models  # noqa: F401 — registers Agent, Conversation, Message, Note
        db.create_all()

        # Verify tables exist, recreate if missing
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        required = {"agent", "conversation", "message", "note", "conversation_participants"}
        missing = required - set(tables)
        if missing:
            log.warning("Missing tables %s, recreating all", missing)
            db.create_all()

        # Verify agent table has preferred_model column
        if "agent" in tables:
            columns = {col["name"] for col in inspector.get_columns("agent")}
            if "preferred_model" not in columns:
                log.warning("Missing preferred_model column, altering table")
                db.session.execute(db.text("ALTER TABLE agent ADD COLUMN preferred_model VARCHAR(256)"))
                db.session.commit()

        log.info("Database verified at %s", DB_PATH)

    # Register blueprints
    _register_blueprints(app)
    _register_template_globals(app)

    # ── Health endpoint ──────────────────────────────────────────────
    @app.route("/health")
    def health():
        try:
            from models import Agent
            agent_count = Agent.query.count()
            return jsonify({
                "status": "healthy",
                "service": "agent-comms",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agents": agent_count,
                "database": "ok",
                "db_path": DB_PATH,
            })
        except Exception as e:
            return jsonify({
                "status": "degraded",
                "service": "agent-comms",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "database": "error",
            }), 503

    # ── Error handlers ───────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        if _wants_json():
            return jsonify({"error": "forbidden", "status": 403}), 403
        return _error_page("Forbidden", "You don't have access to this resource.", 403), 403

    @app.errorhandler(404)
    def not_found(e):
        if _wants_json():
            return jsonify({"error": "not found", "status": 404}), 404
        return _error_page("Not Found", "The page you're looking for doesn't exist.", 404), 404

    @app.errorhandler(500)
    def server_error(e):
        log.error("Internal server error: %s", e)
        if _wants_json():
            return jsonify({"error": "internal server error", "status": 500}), 500
        return _error_page("Server Error", "Something went wrong. The error has been logged.", 500), 500

    @app.errorhandler(503)
    def service_unavailable(e):
        if _wants_json():
            return jsonify({"error": "service unavailable", "status": 503}), 503
        return _error_page("Service Unavailable", "The service is temporarily unavailable.", 503), 503

    # ── Auth middleware ───────────────────────────────────────────────
    AUTH_EMAIL = os.environ.get("AUTH_EMAIL", "cassie@omg.lol")

    @app.before_request
    def _auth_check():
        """Verify exe.dev auth header. Health endpoint and tests bypass auth."""
        from flask import request, abort
        if request.path == "/health":
            return
        if app.config.get("TESTING"):
            return
        email = request.headers.get("X-ExeDev-Email", "")
        if email != AUTH_EMAIL:
            abort(403)

    # ── Before-request: catch DB errors early ────────────────────────
    @app.before_request
    def _check_db():
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception:
            log.error("Database connection failed")
            from flask import abort
            abort(503)

    return app


# ── Helpers ──────────────────────────────────────────────────────────

def _wants_json():
    from flask import request
    accept = request.headers.get("Accept", "")
    path = request.path
    return (
        "application/json" in accept
        or path.startswith("/api/")
        or path == "/health"
    )


def _error_page(title, message, code):
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{code} — {title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0a0a0f;
            color: #e0d8d0;
            font-family: 'Inter', -apple-system, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            text-align: center;
        }}
        .error-container {{ max-width: 480px; padding: 3rem; }}
        .error-code {{ font-size: 4rem; font-weight: 200; color: #FF007F; margin-bottom: 1rem; }}
        .error-title {{ font-size: 1.5rem; font-weight: 600; margin-bottom: 0.75rem; }}
        .error-message {{ color: #888; line-height: 1.6; margin-bottom: 2rem; }}
        a {{ color: #FFD700; text-decoration: none; border-bottom: 1px solid rgba(255,215,0,0.3); }}
        a:hover {{ border-bottom-color: #FFD700; }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">{code}</div>
        <div class="error-title">{title}</div>
        <div class="error-message">{message}</div>
        <a href="/">← Back to Dashboard</a>
    </div>
</body>
</html>"""


def _register_blueprints(app):
    from routes import dashboard_bp
    app.register_blueprint(dashboard_bp)
    try:
        from api import api_bp
        app.register_blueprint(api_bp)
    except ImportError:
        pass


def _register_template_globals(app):
    from routes import register_template_globals
    register_template_globals(app)
