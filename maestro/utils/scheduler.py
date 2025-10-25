import importlib
import json
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any, TypedDict
from uuid import uuid4

from apscheduler.jobstores.base import JobLookupError  # type:ignore[import-untyped]
from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from flask import current_app
from structlog.stdlib import get_logger

from maestro.integrations.redis import CachePrefix, RedisClient
from maestro.utils.dates import IntervalSeconds, local_now

log = get_logger()


class JobMetadata(TypedDict):
    id: str
    run_time: str  # ISO format
    module_path: str
    func_name: str
    kwargs: dict[str, Any]


class JobScheduler:
    """Delayed function execution service for future function invocation"""

    run_time_limit = IntervalSeconds.THIRTY_DAYS

    def __init__(
        self,
        apscheduler: BackgroundScheduler | None = None,
        redis_client: RedisClient | None = None,
    ) -> None:
        self.apscheduler = apscheduler or current_app.scheduler  # type:ignore[attr-defined]
        if not isinstance(self.apscheduler, BackgroundScheduler):
            raise TypeError
        self.redis_client = redis_client or RedisClient()

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
        if run_time > local_now() + timedelta(seconds=self.run_time_limit):
            raise ValueError("Cannot schedule job beyond run_time_limit")

        job_id = job_id or str(uuid4())
        func_name = func.__name__
        module_path = func.__module__

        if module_path is None:
            raise AttributeError("Failed to schedule job becuase function has no module path")

        job_metadata: JobMetadata = {
            "id": job_id or str(uuid4()),
            "run_time": run_time.isoformat(),
            "module_path": module_path,
            "func_name": func_name,
            "kwargs": func_params or {},
        }

        self._cache_job_to_redis(job_metadata)
        self._schedule_job_in_apscheduler(job_metadata, func)

        log.info("Scheduled future job", **job_metadata)

        return job_id

    def cancel_job(self, job_id: str) -> None:
        redis_key = self.redis_client.build_key(CachePrefix.SCHEDULED, job_id)
        self.redis_client.delete(redis_key)
        with suppress(JobLookupError):
            self.apscheduler.remove_job(job_id)
            log.info("Removed job from APScheduler", job_id=job_id)

    def restore_cached_jobs(self) -> None:
        """Loads all cached job metadata and re-schedules them in APScheduler"""
        pattern = self.redis_client.build_key(CachePrefix.SCHEDULED, "*")

        if not (job_keys := self.redis_client.get_keys(pattern)):
            log.info("No cached jobs found in Redis")
            return

        for job_key in job_keys:
            if not (job_json := self.redis_client.get(job_key)):
                continue

            job: JobMetadata = json.loads(job_json)

            if datetime.fromisoformat(job["run_time"]) < local_now():
                log.warning("Cached job has run_time in the past - deleting job", **job)
                self.redis_client.delete(job_key)
                continue

            try:
                func = self._resolve_function(job["module_path"], job["func_name"])
            except Exception:
                log.exception("Failed to restore cached job", **job)

            self._schedule_job_in_apscheduler(job, func)
            log.info("Restored job from cache", job_id=job["id"])

    def _cache_job_to_redis(self, job: JobMetadata) -> None:
        """Persist job metadata to Redis so that we don't lose jobs between restarts"""
        redis_key = self.redis_client.build_key(CachePrefix.SCHEDULED, job["id"])
        job_json = json.dumps(job)

        self.redis_client.set(redis_key, job_json, ttl_seconds=self.run_time_limit)
        log.debug("Cached job to Redis", job_id=job["id"], redis_key=redis_key)

    def _schedule_job_in_apscheduler(self, job: JobMetadata, func: Callable) -> None:
        """Schedule a job in APScheduler with a wrapper that cleans up Redis after execution"""
        run_time = datetime.fromisoformat(job["run_time"])
        func_name = f"{job['module_path']}.{job['func_name']}"

        def job_wrapper() -> None:
            try:
                log.info("Executing scheduled job", job_id=job["id"], func=func_name)
                func(**job["kwargs"])
            except Exception:
                log.exception("Error executing scheduled job", job_id=job["id"])
            finally:
                redis_key = self.redis_client.build_key(CachePrefix.SCHEDULED, job["id"])
                self.redis_client.delete(redis_key)

        self.apscheduler.add_job(
            func=job_wrapper,
            trigger="date",
            run_date=run_time,
            id=job["id"],
            name=func_name,
            replace_existing=True,
        )

    def _resolve_function(self, module_path: str, func_name: str) -> Callable:
        """Dynamically import a module and retrieve a function by name"""
        module = importlib.import_module(module_path)
        func: Callable = getattr(module, func_name)

        if not callable(func):
            raise TypeError(f"{module_path}.{func_name} is not callable")

        return func
