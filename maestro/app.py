import atexit
import os
from enum import StrEnum, auto
from http import HTTPMethod
from typing import Any

from apscheduler.executors.pool import ThreadPoolExecutor  # type:ignore[import-untyped]
from apscheduler.jobstores.redis import RedisJobStore  # type:ignore[import-untyped]
from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy

from maestro.config import (
    DATABASE_URL,
    REDIS_HOST,
    REDIS_PORT,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    TIMEZONE,
)
from maestro.integrations.home_assistant.websocket_manager import WebSocketManager
from maestro.triggers.cron import CronTriggerManager
from maestro.triggers.maestro import MaestroEvent, MaestroTriggerManager
from maestro.triggers.sun import SunTriggerManager
from maestro.utils.internal import configure_logging, load_script_modules, test_mode_active
from maestro.utils.logging import build_process_id, log, set_process_id
from maestro.webhooks.event_fired import handle_event_fired
from maestro.webhooks.hass_shutdown import handle_hass_shutdown
from maestro.webhooks.hass_startup import handle_hass_startup
from maestro.webhooks.notif_action import handle_notif_action
from maestro.webhooks.state_changed import handle_state_changed


class MaestroFlask(Flask):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        process_id = build_process_id("startup")
        set_process_id(process_id)
        self._initialize_db()

        if test_mode_active():
            self._initialize_test_environment()
            return

        load_script_modules()
        self._initialize_scheduler()
        self._initialize_websocket()
        with self.app_context():
            MaestroTriggerManager.fire_triggers(MaestroEvent.STARTUP)
        atexit.register(self._shutdown_handler)

    def _initialize_db(self) -> None:
        self.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        self.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
        db.init_app(self)

    def _initialize_scheduler(self) -> None:
        self.scheduler = BackgroundScheduler(
            jobstores={"default": RedisJobStore(host=REDIS_HOST, port=REDIS_PORT)},
            executors={"default": ThreadPoolExecutor(max_workers=100)},
            timezone=TIMEZONE,
        )
        self.scheduler.start()
        CronTriggerManager.register_jobs(self.scheduler)
        SunTriggerManager.register_jobs(self.scheduler)
        atexit.register(self.scheduler.shutdown)

    def _initialize_websocket(self) -> None:
        self.websocket_manager = WebSocketManager()
        self.websocket_manager.start()
        atexit.register(self.websocket_manager.stop)

    def _shutdown_handler(self) -> None:
        self.app_context().push()
        MaestroTriggerManager.fire_triggers(MaestroEvent.SHUTDOWN, self)

    def _initialize_test_environment(self) -> None:
        """Initialize in-memory scheduler for registering decorators while testing."""
        self.scheduler = BackgroundScheduler(timezone=TIMEZONE)


configure_logging()


class EventType(StrEnum):
    STATE_CHANGED = auto()
    IOS_NOTIF_ACTION = "ios.notification_action_fired"
    HASS_STARTED = "maestro_hass_started"
    HASS_STOPPED = "homeassistant_final_write"


db = SQLAlchemy()
app = MaestroFlask(__name__)


@app.shell_context_processor
def make_shell_context() -> dict:
    """Pre-load common imports for flask shell command"""
    from maestro.integrations.home_assistant.client import HomeAssistantClient
    from maestro.integrations.home_assistant.types import (
        AttributeId,
        EntityData,
        EntityId,
        StateChangeEvent,
        StateId,
    )
    from maestro.integrations.redis import RedisClient
    from maestro.integrations.state_manager import StateManager
    from maestro.registry.registry_manager import RegistryManager
    from maestro.triggers.sun import SolarEvent
    from maestro.triggers.trigger_manager import TriggerManager
    from maestro.utils import (
        IntervalSeconds,
        JobScheduler,
        Notif,
        local_now,
        resolve_timestamp,
    )

    hass = HomeAssistantClient()
    redis = RedisClient()
    sm = StateManager(hass_client=hass, redis_client=redis)
    registry = TriggerManager.get_registry()

    return locals()
