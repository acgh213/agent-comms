from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
socketio = SocketIO()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    socketio.init_app(app, async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "eventlet"))

    with app.app_context():
        _init_models()
        db.create_all()

    # Register API blueprint
    _register_blueprints(app)

    return app


def _register_blueprints(app):
    """Register all application blueprints."""
    try:
        from api import api_bp

        app.register_blueprint(api_bp)
    except ImportError:
        pass  # api module not yet created


def _init_models():
    """Import all models so SQLAlchemy knows about them."""
    try:
        from models import (  # noqa: F401
            Agent,
            Conversation,
            Message,
            Note,
            conversation_participants,
        )
    except ImportError:
        pass  # models not yet created

