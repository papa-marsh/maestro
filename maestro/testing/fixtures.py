from collections.abc import Generator

import pytest
from flask import Flask

from maestro.app import db
from maestro.testing.context import reset_test_context
from maestro.testing.maestro_test import MaestroTest


@pytest.fixture
def mt() -> Generator[MaestroTest]:
    """
    Main pytest fixture providing a clean test context for each test.
    This fixture is automatically reset between tests, ensuring isolation.
    All entities will automatically use the test's mock state manager.
    """
    # Create a minimal Flask app for trigger functions that need app context
    # We use a basic Flask app instead of MaestroFlask to avoid heavy initialization
    app = Flask("maestro_test")

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    context = MaestroTest()
    app.scheduler = context.job_scheduler  # type: ignore[attr-defined]

    with app.app_context():
        db.create_all()
        yield context
        db.session.remove()
        db.drop_all()

    context.reset()
    reset_test_context()
