"""Agent Comms — Flask application factory."""

import logging
import os
import traceback
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
socketio = SocketIO()

log = logging.getLogger("agent-comms")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

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
        log.info("Database tables verified")

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
            return  # health check bypasses auth
        if app.config.get("TESTING"):
            return  # tests bypass auth
        email = request.headers.get("X-ExeDev-Email", "")
        if email != AUTH_EMAIL:
            abort(403)

    # ── Before-request: catch DB errors early ────────────────────────
    @app.before_request
    def _check_db():
        """Verify DB is accessible before processing any request."""
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception:
            log.error("Database connection failed")
            from flask import abort
            abort(503)

    # ── After-request: log slow requests ─────────────────────────────
    @app.after_request
    def _log_request(response):
        if response.status_code >= 500:
            log.error("%s %s → %s", request_method(), request_path(), response.status_code)
        return response

    return app


# ── Helpers ──────────────────────────────────────────────────────────

def _wants_json():
    """Check if the request prefers JSON (API call vs browser)."""
    from flask import request
    accept = request.headers.get("Accept", "")
    path = request.path
    return (
        "application/json" in accept
        or path.startswith("/api/")
        or path == "/health"
    )


def _error_page(title, message, code):
    """Render a minimal dark-themed error page."""
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
        .error-container {{
            max-width: 480px;
            padding: 3rem;
        }}
        .error-code {{
            font-size: 4rem;
            font-weight: 200;
            color: #FF007F;
            margin-bottom: 1rem;
        }}
        .error-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }}
        .error-message {{
            color: #888;
            line-height: 1.6;
            margin-bottom: 2rem;
        }}
        a {{
            color: #FFD700;
            text-decoration: none;
            border-bottom: 1px solid rgba(255, 215, 0, 0.3);
        }}
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


def request_method():
    from flask import request
    return request.method


def request_path():
    from flask import request
    return request.path


def _register_blueprints(app):
    """Register all application blueprints."""
    from routes import dashboard_bp
    app.register_blueprint(dashboard_bp)

    try:
        from api import api_bp
        app.register_blueprint(api_bp)
    except ImportError:
        pass


def _register_template_globals(app):
    """Register template filters and context processors."""
    from routes import register_template_globals
    register_template_globals(app)
