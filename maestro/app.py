import atexit
from http import HTTPMethod
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from structlog.stdlib import get_logger

from maestro.config import DATABASE_URL, SQLALCHEMY_TRACK_MODIFICATIONS, TIMEZONE
from maestro.routes.event_fired import handle_event_fired
from maestro.routes.state_changed import handle_state_changed
from maestro.triggers.cron import CronTriggerManager
from maestro.utils.infra import load_script_modules


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
        atexit.register(lambda: self.scheduler.shutdown())


db = SQLAlchemy()
app = MaestroFlask(__name__)

log = get_logger()


@app.shell_context_processor
def make_shell_context() -> dict:
    """Pre-load common imports for flask shell command"""
    from maestro.integrations.home_assistant.client import HomeAssistantClient
    from maestro.integrations.home_assistant.types import (
        AttributeId,
        Domain,
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
    from maestro.triggers.trigger_manager import TriggerManager
    from maestro.utils import IntervalSeconds, local_now, resolve_timestamp
    from maestro.utils.registry_manager import RegistryManager

    hass = HomeAssistantClient()
    redis = RedisClient()
    sm = StateManager(hass_client=hass, redis_client=redis)

    return locals()


@app.before_request
def before_request() -> None:
    log.info("Request received", path=request.path, method=request.method)


@app.route("/")
def hello_world() -> str:
    return "<p>Hello, World!</p>"


@app.route("/events/state-changed", methods=[HTTPMethod.POST])
def state_changed() -> tuple[Response, int]:
    app.logger.info("Handling webhook: state changed")
    return handle_state_changed()


@app.route("/events/event-fired", methods=[HTTPMethod.POST])
def event_fired() -> tuple[Response, int]:
    app.logger.info("Handling webhook: event fired")
    return handle_event_fired()
