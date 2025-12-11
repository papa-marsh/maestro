import os

import pytest

pytest_plugins = ["maestro.testing.fixtures"]

# Force SQLite in-memory database for tests, overriding any .env settings
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def setup_database_tables():
    """
    Create database tables automatically for all tests.
    This runs after pytest_configure but before any tests execute.
    """
    from maestro.app import app, db

    with app.app_context():
        db.create_all()
        yield
        db.drop_all()
