import pytest
from app import create_app, db as _db


@pytest.fixture
def app():
    """Create application with in-memory SQLite for testing."""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SOCKETIO_ASYNC_MODE": None,
        }
    )

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Database instance within app context."""
    with app.app_context():
        yield _db
