import atexit
from http import HTTPMethod
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from flask import Flask, Response, request
from structlog.stdlib import get_logger

from maestro.config import TIMEZONE
from maestro.routes.state_changed import handle_state_changed
from maestro.triggers.cron import CronTriggerManager
from maestro.utils.infra import load_script_modules


class MaestroFlask(Flask):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        load_script_modules()

        self.scheduler = BackgroundScheduler(timezone=TIMEZONE)  # TODO: Migrate to AsyncIOScheduler
        self.scheduler.start()
        CronTriggerManager.register_jobs(self.scheduler)
        atexit.register(lambda: self.scheduler.shutdown())

        super().__init__(*args, **kwargs)


app = MaestroFlask(__name__)
log = get_logger()


@app.shell_context_processor
def make_shell_context() -> dict:
    """Pre-load common imports for flask shell command"""
    from maestro.domains import Calendar, Climate, Switch
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
        light,
        lock,
        media_player,
        number,
        person,
        pyscript,
        sensor,
        sun,
        switch,
        weather,
    )
    from maestro.triggers.trigger_manager import TriggerManager
    from maestro.utils import local_now, resolve_timestamp
    from maestro.utils.misc import validate_attributes

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
    app.logger.info("Handling state change event")
    return handle_state_changed()
