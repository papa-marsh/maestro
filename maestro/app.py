import atexit
from enum import StrEnum, auto
from http import HTTPMethod
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from structlog.stdlib import get_logger

from maestro.config import DATABASE_URL, SQLALCHEMY_TRACK_MODIFICATIONS, TIMEZONE
from maestro.triggers.cron import CronTriggerManager
from maestro.triggers.maestro import MaestroEvent, MaestroTriggerManager
from maestro.triggers.sun import SunTriggerManager
from maestro.utils.internal import configure_logging, load_script_modules
from maestro.utils.scheduler import JobScheduler
from maestro.webhooks.event_fired import handle_event_fired
from maestro.webhooks.hass_shutdown import handle_hass_shutdown
from maestro.webhooks.hass_startup import handle_hass_startup
from maestro.webhooks.notif_action import handle_notif_action
from maestro.webhooks.state_changed import handle_state_changed


class MaestroFlask(Flask):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._initialize_db()
        load_script_modules()
        self._initialize_scheduler()
        with self.app_context():
            MaestroTriggerManager.fire_triggers(MaestroEvent.STARTUP_NOT_WORKING_YET)
        atexit.register(self._shutdown_handler)

    def _initialize_db(self) -> None:
        self.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        self.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
        db.init_app(self)

    def _initialize_scheduler(self) -> None:
        self.scheduler = BackgroundScheduler(timezone=TIMEZONE)
        self.scheduler.start()
        JobScheduler(self.scheduler).restore_cached_jobs()
        CronTriggerManager.register_jobs(self.scheduler)
        SunTriggerManager.register_jobs(self.scheduler)
        atexit.register(self.scheduler.shutdown)

    def _shutdown_handler(self) -> None:
        self.app_context().push()
        MaestroTriggerManager.fire_triggers(MaestroEvent.SHUTDOWN, self)


configure_logging()
log = get_logger()


class EventType(StrEnum):
    STATE_CHANGED = auto()
    IOS_NOTIF_ACTION = "ios.notification_action_fired"
    HASS_STARTED = "homeassistant_started"  # TODO: Verify
    HASS_STOPPED = "homeassistant_final_write"  # TODO: Verify


WEBHOOK_HANDLERS = {
    EventType.STATE_CHANGED: handle_state_changed,
    EventType.IOS_NOTIF_ACTION: handle_notif_action,
    EventType.HASS_STARTED: handle_hass_startup,
    EventType.HASS_STOPPED: handle_hass_shutdown,
}

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
    from maestro.registry import (
        binary_sensor,
        button,
        calendar,
        climate,
        cover,
        device_tracker,
        event,
        fan,
        humidifier,
        input_boolean,
        input_number,
        input_select,
        input_text,
        light,
        lock,
        maestro,
        media_player,
        number,
        person,
        select,
        sensor,
        sun,
        switch,
        update,
        weather,
        zone,
    )
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


@app.route("/webhooks/hass_event", methods=[HTTPMethod.POST])
def event_fired() -> tuple[Response, int]:
    request_body = request.get_json() or {}
    event_type = request_body["event_type"]
    log.info("HASS event webhook received", event_type=event_type)

    webhook_handler = WEBHOOK_HANDLERS.get(event_type, handle_event_fired)

    return webhook_handler(request_body)
