import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "agent-comms-dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///agent_comms.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SOCKETIO_ASYNC_MODE = "eventlet"
