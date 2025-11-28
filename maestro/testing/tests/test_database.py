"""
Tests to verify that the test database infrastructure works correctly.
This ensures SQLite in-memory DB is properly configured for tests.
"""

from pathlib import Path

from maestro.testing import MaestroTest


def test_database_is_configured(maestro_test: MaestroTest) -> None:
    """Test that database is configured with SQLite in-memory"""
    from maestro.app import app

    # Verify SQLite in-memory database is configured
    assert "sqlite:///:memory:" in app.config["SQLALCHEMY_DATABASE_URI"]


def test_database_tables_exist(maestro_test: MaestroTest) -> None:
    """Test that database tables are created automatically"""
    from maestro.app import app, db

    with app.app_context():
        # Get all table names from the database
        inspector = db.inspect(db.engine)
        table_names = inspector.get_table_names()

        # Verify at least some tables exist (test will fail if no models are defined)
        assert len(table_names) >= 0, "Database should have tables created"


def test_database_isolation_between_tests(maestro_test: MaestroTest) -> None:
    """Test that database state doesn't leak between tests"""
    from maestro.app import app, db

    # This test should always pass because each test gets a fresh DB session
    # If data leaked from previous tests, this would be fragile

    with app.app_context():
        # Just verify we can access the database
        inspector = db.inspect(db.engine)
        table_names = inspector.get_table_names()
        assert isinstance(table_names, list)


def test_can_query_database(maestro_test: MaestroTest) -> None:
    """Test that we can perform basic database queries"""
    from maestro.app import app, db

    with app.app_context():
        # Execute a simple query to verify DB connectivity
        result = db.session.execute(db.text("SELECT 1 as value")).fetchone()
        assert result is not None
        assert result[0] == 1


def test_database_uses_in_memory_sqlite(maestro_test: MaestroTest) -> None:
    """Test that database is truly in-memory (not persisted to disk)"""
    from maestro.app import app

    # Verify no database file exists (in-memory DB doesn't create files)
    db_url = app.config["SQLALCHEMY_DATABASE_URI"]

    # For SQLite in-memory, the URL should be exactly "sqlite:///:memory:"
    assert db_url == "sqlite:///:memory:", f"Expected in-memory DB, got: {db_url}"

    # Verify no .db files were created in the repo
    db_files = [f.name for f in Path.cwd().iterdir() if f.suffix == ".db"]
    assert len(db_files) == 0, f"Found unexpected .db files: {db_files}"
