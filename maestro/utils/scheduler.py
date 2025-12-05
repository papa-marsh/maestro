from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from uuid import uuid4

from apscheduler.job import Job  # type:ignore[import-untyped]
from apscheduler.jobstores.base import JobLookupError  # type:ignore[import-untyped]
from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from flask import current_app

from maestro.utils.dates import IntervalSeconds, local_now
from maestro.utils.exceptions import SchedulerMisconfiguredError
from maestro.utils.internal import test_mode_active
from maestro.utils.logging import log


class JobScheduler:
    """Delayed function execution service for future function invocation"""

    run_time_limit = IntervalSeconds.THIRTY_DAYS

    def __init__(self, apscheduler: BackgroundScheduler | None = None) -> None:
        self.apscheduler = apscheduler or current_app.scheduler  # type: ignore[attr-defined]

        if not test_mode_active() and not isinstance(self.apscheduler, BackgroundScheduler):
            raise SchedulerMisconfiguredError

    def schedule_job(
        self,
        run_time: datetime,
        func: Callable,
        func_params: dict | None = None,
        job_id: str | None = None,
    ) -> str:
        """Schedule a function to run in the future. Returns the job ID"""
        if run_time < local_now():
            raise ValueError("Cannot schedule job in the past")

        job_id = job_id or str(uuid4())
        func_name = f"{func.__module__}.{func.__name__}"

        self.apscheduler.add_job(
            func=func,
            trigger="date",
            run_date=run_time,
            id=job_id,
            name=func_name,
            kwargs=func_params or {},
            replace_existing=True,
        )

        log.info(
            "Scheduled future job",
            job_id=job_id,
            run_time=run_time.isoformat(),
            func=func_name,
        )

        return job_id

    def get_job(self, job_id: str) -> Job | None:
        """Get a scheduled job by ID. Returns None if job doesn't exist."""
        try:
            return self.apscheduler.get_job(job_id)
        except JobLookupError:
            return None

    def cancel_job(self, job_id: str) -> None:
        """Cancel a scheduled job by ID if it exists."""
        with suppress(JobLookupError):
            self.apscheduler.remove_job(job_id)
            log.info("Removed job from APScheduler", job_id=job_id)
