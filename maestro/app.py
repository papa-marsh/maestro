import atexit
from http import HTTPMethod

from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from flask import Flask, Response, request
from structlog.stdlib import get_logger

from maestro.routes.state_changed import handle_state_changed
from maestro.triggers.cron import CronTriggerManager

app = Flask(__name__)
log = get_logger()

# TODO: Migrate to AsyncIOScheduler
app.scheduler = BackgroundScheduler()  # type:ignore[attr-defined]
app.scheduler.start()  # type:ignore[attr-defined]
CronTriggerManager.register_jobs(app.scheduler)  # type:ignore[attr-defined]
atexit.register(lambda: app.scheduler.shutdown())  # type:ignore[attr-defined]


@app.shell_context_processor
def make_shell_context() -> dict:
    """Pre-load common imports for flask shell command"""
    from maestro.domains.climate import Climate
    from maestro.domains.entity import Entity
    from maestro.domains.switch import Switch
    from maestro.integrations.home_assistant.client import HomeAssistantClient
    from maestro.integrations.home_assistant.types import (
        AttributeId,
        Domain,
        EntityId,
        EntityResponse,
        StateChangeEvent,
        StateId,
    )
    from maestro.integrations.redis import RedisClient
    from maestro.integrations.state_manager import StateManager
    from maestro.triggers.trigger_manager import TriggerManager
    from maestro.utils.dates import resolve_timestamp, utc_now

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
