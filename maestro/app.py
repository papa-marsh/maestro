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
from maestro.triggers.sun import SunTriggerManager
from maestro.utils.infra import load_script_modules
from maestro.webhooks.event_fired import handle_event_fired
from maestro.webhooks.notif_action import handle_notif_action
from maestro.webhooks.state_changed import handle_state_changed


class MaestroFlask(Flask):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._initialize_db()
        load_script_modules()
        self._initialize_scheduler()

    def _initialize_db(self) -> None:
        self.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        self.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
        db.init_app(self)  # type: ignore[no-untyped-call]

    def _initialize_scheduler(self) -> None:
        self.scheduler = BackgroundScheduler(timezone=TIMEZONE)
        self.scheduler.start()
        CronTriggerManager.register_jobs(self.scheduler)
        SunTriggerManager.register_jobs(self.scheduler)
        atexit.register(lambda: self.scheduler.shutdown())


db = SQLAlchemy()
app = MaestroFlask(__name__)

log = get_logger()


class EventType(StrEnum):
    STATE_CHANGED = auto()
    IOS_NOTIF_ACTION = "ios.notification_action_fired"


WEBHOOK_HANDLERS = {
    EventType.STATE_CHANGED: handle_state_changed,
    EventType.IOS_NOTIF_ACTION: handle_notif_action,
}


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
    from maestro.triggers.sun import SolarEvent
    from maestro.triggers.trigger_manager import TriggerManager
    from maestro.utils import (
        IntervalSeconds,
        Notif,
        NotifPriority,
        local_now,
        resolve_timestamp,
    )
    from maestro.utils.registry_manager import RegistryManager

    hass = HomeAssistantClient()
    redis = RedisClient()
    sm = StateManager(hass_client=hass, redis_client=redis)

    return locals()


@app.route("/webhooks/hass_event", methods=[HTTPMethod.POST])
def event_fired() -> tuple[Response, int]:
    request_body = request.get_json() or {}
    event_type = request_body["event_type"]
    log.info("HASS event webhook received", event_type=event_type)

    webhook_handler = WEBHOOK_HANDLERS.get(event_type, handle_event_fired)

    return webhook_handler(request_body)
