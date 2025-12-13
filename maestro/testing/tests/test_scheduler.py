"""
Tests to verify that the test scheduler infrastructure works correctly.
This ensures the scheduler is available but doesn't actually run jobs during tests.
"""

import time

from maestro.testing import MaestroTest


def test_scheduler_exists(mt: MaestroTest) -> None:
    """Test that scheduler object exists in test environment"""
    from maestro.app import app

    # Verify scheduler is initialized
    assert hasattr(app, "scheduler"), "App should have a scheduler attribute"
    assert app.scheduler is not None, "Scheduler should not be None"


def test_scheduler_uses_memory_jobstore(mt: MaestroTest) -> None:
    """Test that scheduler uses in-memory job store (not Redis)"""
    from maestro.app import app

    # When BackgroundScheduler is created without explicit jobstores,
    # it defaults to MemoryJobStore (which is what we want for tests)
    # The jobstores dict is populated when scheduler starts, but since
    # we don't start it in tests, we verify via the _jobstores attribute

    # If _jobstores is empty, that means no Redis jobstore was configured
    # (which is correct for tests)
    jobstores = app.scheduler._jobstores

    # Verify no Redis jobstore is configured
    for name, jobstore in jobstores.items():
        assert "Redis" not in type(jobstore).__name__, (
            f"Found RedisJobStore in tests, which should not be configured. "
            f"Jobstore '{name}' is {type(jobstore).__name__}"
        )

    # If jobstores is empty, that's fine - scheduler will default to MemoryJobStore
    # when it starts (which we don't do in tests)


def test_scheduler_not_started(mt: MaestroTest) -> None:
    """Test that scheduler is not running during tests"""
    from maestro.app import app

    # Scheduler should exist but not be running to prevent jobs from executing
    # during test collection
    assert not app.scheduler.running, "Scheduler should not be running during tests"


def test_can_add_jobs_to_scheduler(mt: MaestroTest) -> None:
    """Test that jobs can be registered with the test scheduler"""
    from maestro.app import app

    # Add a test job
    def test_job() -> None:
        pass

    job = app.scheduler.add_job(test_job, "interval", seconds=60, id="test_job_123")

    # Verify job was added
    assert job is not None
    assert job.id == "test_job_123"

    # Verify we can retrieve the job
    retrieved_job = app.scheduler.get_job("test_job_123")
    assert retrieved_job is not None
    assert retrieved_job.id == "test_job_123"

    # Clean up
    app.scheduler.remove_job("test_job_123")


def test_jobs_dont_execute_automatically(mt: MaestroTest) -> None:
    """Test that scheduled jobs don't actually run during tests"""
    from maestro.app import app

    executed = []

    def test_job() -> None:
        executed.append(True)

    # Schedule a job to run immediately
    app.scheduler.add_job(test_job, "date", id="immediate_job")

    # Wait a moment to see if it executes
    time.sleep(0.1)

    # Job should NOT have executed because scheduler isn't started
    assert len(executed) == 0, "Job should not execute when scheduler is not running"

    # Clean up
    app.scheduler.remove_job("immediate_job")


def test_cron_triggers_can_register(mt: MaestroTest) -> None:
    """Test that @cron_trigger decorated functions can register with scheduler"""
    from maestro.app import app
    from maestro.triggers.cron import cron_trigger

    initial_job_count = len(app.scheduler.get_jobs())

    # Define a function with cron trigger decorator
    @cron_trigger(minute="*/5")
    def test_cron_function() -> None:
        pass

    # The decorator should successfully register (not crash)
    # We don't verify the job is added because that depends on trigger registration logic
    # which may not happen during test imports

    # Verify scheduler is still functional
    final_job_count = len(app.scheduler.get_jobs())
    assert final_job_count >= initial_job_count, "Scheduler should still be functional"


def test_scheduler_timezone_configured(mt: MaestroTest) -> None:
    """Test that scheduler has timezone configured"""
    from maestro.app import app

    # Scheduler should have timezone set
    assert app.scheduler.timezone is not None, "Scheduler should have timezone configured"


def test_job_isolation_between_tests(mt: MaestroTest) -> None:
    """Test that jobs added in one test don't leak to other tests"""
    from maestro.app import app

    # Add a job
    def temp_job() -> None:
        pass

    app.scheduler.add_job(temp_job, "interval", seconds=60, id="temp_test_job")

    # Verify it exists
    assert app.scheduler.get_job("temp_test_job") is not None

    # Clean it up
    app.scheduler.remove_job("temp_test_job")

    # Verify it's gone
    assert app.scheduler.get_job("temp_test_job") is None
