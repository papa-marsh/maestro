"""
Tests for job scheduling in the testing framework.
Verifies that JobScheduler uses mock APScheduler and tracks scheduled jobs.
"""

from datetime import timedelta

from maestro.testing.maestro_test import MaestroTest
from maestro.utils.dates import local_now
from maestro.utils.scheduler import JobScheduler


def test_job_scheduler_uses_mock(mt: MaestroTest) -> None:
    """Test that JobScheduler automatically uses mock in test mode"""

    def example_function() -> None:
        pass

    # Create JobScheduler without passing apscheduler - should auto-detect test mode
    scheduler = JobScheduler()

    # Schedule a job
    run_time = local_now() + timedelta(hours=1)
    job_id = scheduler.schedule_job(
        run_time=run_time,
        func=example_function,
    )

    # Verify it was scheduled in the mock
    mt.assert_job_scheduled(job_id, example_function)

    # Get the job and verify details
    job = mt.get_scheduled_job(job_id)
    assert job.func == example_function


def test_cancel_scheduled_job(mt: MaestroTest) -> None:
    """Test canceling a scheduled job"""

    def example_function() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)
    job_id = scheduler.schedule_job(run_time, example_function)

    # Verify it was scheduled
    mt.assert_job_scheduled(job_id, example_function)

    # Cancel the job
    scheduler.cancel_job(job_id)

    # Verify it's no longer scheduled
    mt.assert_job_not_scheduled(job_id)


def test_get_all_scheduled_jobs(mt: MaestroTest) -> None:
    """Test getting all scheduled jobs"""

    def func1() -> None:
        pass

    def func2() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)

    # Schedule multiple jobs
    job_id1 = scheduler.schedule_job(run_time, func1)
    job_id2 = scheduler.schedule_job(run_time, func2)

    # Get all jobs
    jobs = mt.get_scheduled_jobs()
    assert len(jobs) == 2

    job_ids = [job.id for job in jobs]
    assert job_id1 in job_ids
    assert job_id2 in job_ids


def test_scheduled_job_isolation_between_tests(mt: MaestroTest) -> None:
    """Test that scheduled jobs are cleared between tests"""

    def example_function() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)

    # Schedule a job
    scheduler.schedule_job(run_time, example_function, job_id="isolation_test_job")

    # Verify it was scheduled
    mt.assert_job_scheduled("isolation_test_job", example_function)

    # Manually reset (simulating what happens between tests)
    mt.reset()

    # Verify the job is gone after reset
    mt.assert_job_not_scheduled("isolation_test_job")


def test_schedule_job_with_custom_id(mt: MaestroTest) -> None:
    """Test scheduling a job with a custom job ID"""

    def example_function() -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)
    custom_job_id = "my_custom_job_id"

    # Schedule with custom ID
    job_id = scheduler.schedule_job(run_time, example_function, job_id=custom_job_id)

    assert job_id == custom_job_id
    mt.assert_job_scheduled(custom_job_id, example_function)


def test_schedule_job_with_params(mt: MaestroTest) -> None:
    """Test scheduling a job with function parameters"""

    def example_function(param1: str, param2: int) -> None:
        pass

    scheduler = JobScheduler()
    run_time = local_now() + timedelta(hours=1)
    func_params = {"param1": "test", "param2": 42}

    job_id = scheduler.schedule_job(run_time, example_function, func_params=func_params)

    # Get the job and verify params were stored
    job = mt.get_scheduled_job(job_id)
    assert job.kwargs == func_params
