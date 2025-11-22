"""Mock job scheduler for testing without APScheduler."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from maestro.utils.dates import local_now


@dataclass
class ScheduledJob:
    """Records a scheduled job for testing."""

    job_id: str
    run_time: datetime
    func: Callable
    func_params: dict[str, Any]
    func_name: str
    scheduled_at: datetime = field(default_factory=local_now)


class MockJobScheduler:
    """
    Mock JobScheduler that records scheduled jobs without executing them.

    This allows testing that jobs are scheduled correctly without waiting
    for them to execute or dealing with background scheduler complexity.
    """

    def __init__(self) -> None:
        self._scheduled_jobs: dict[str, ScheduledJob] = {}

    def schedule_job(
        self,
        run_time: datetime,
        func: Callable,
        func_params: dict | None = None,
        job_id: str | None = None,
    ) -> str:
        """Record a scheduled job without actually scheduling it."""
        from uuid import uuid4

        if run_time < local_now():
            raise ValueError("Cannot schedule job in the past")

        job_id = job_id or str(uuid4())
        func_name = f"{func.__module__}.{func.__name__}"

        scheduled_job = ScheduledJob(
            job_id=job_id,
            run_time=run_time,
            func=func,
            func_params=func_params or {},
            func_name=func_name,
        )

        self._scheduled_jobs[job_id] = scheduled_job

        return job_id

    def get_job(self, job_id: str) -> ScheduledJob | None:
        """Get a scheduled job by ID."""
        return self._scheduled_jobs.get(job_id)

    def cancel_job(self, job_id: str) -> None:
        """Cancel (remove) a scheduled job by ID."""
        if job_id in self._scheduled_jobs:
            del self._scheduled_jobs[job_id]

    def get_all_jobs(self) -> list[ScheduledJob]:
        """Get all scheduled jobs."""
        return list(self._scheduled_jobs.values())

    def execute_job(self, job_id: str) -> Any:
        """
        Manually execute a scheduled job for testing.

        This allows you to test the job's logic without waiting for
        the scheduled time.
        """
        job = self._scheduled_jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")

        return job.func(**job.func_params)

    def clear(self) -> None:
        """Clear all scheduled jobs."""
        self._scheduled_jobs.clear()
