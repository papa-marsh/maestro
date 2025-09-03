import json
import logging
from enum import StrEnum, auto
from http import HTTPMethod

from flask import Flask, Response, request

from maestro.routes.state_changed import handle_state_changed

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.shell_context_processor
def make_shell_context() -> dict:
    """Pre-load common imports for flask shell command"""
    from maestro.entities.climate import Climate
    from maestro.entities.domain import Domain
    from maestro.entities.entity import Entity
    from maestro.entities.switch import Switch
    from maestro.integrations.home_assistant import (
        EntityResponse,
        HomeAssistantClient,
        StateChangeEvent,
    )
    from maestro.integrations.redis import RedisClient
    from maestro.integrations.state_manager import StateManager
    from maestro.utils.dates import resolve_timestamp, utc_now

    # Convenience instances
    hass = HomeAssistantClient()
    redis = RedisClient()
    sm = StateManager(hass_client=hass, redis_client=redis)

    return locals()  # Returns all local variables as a dict


class EventType(StrEnum):
    STATE_CHANGED = auto()


@app.route("/")
def hello_world() -> str:
    app.logger.info("Hello World")
    return "<p>Hello, World!</p>"


@app.route("/payload-testing", methods=[HTTPMethod.POST])
def payload_testing() -> str:
    request_body = request.get_json() or {}
    app.logger.info(f"Request body: {json.dumps(request_body, indent=2)}")
    return "<p>Payload Testing</p>"


@app.route("/events/state-changed", methods=[HTTPMethod.POST])
def state_changed() -> tuple[Response, int]:
    return handle_state_changed()
