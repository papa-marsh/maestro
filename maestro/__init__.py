import json
import logging
from enum import StrEnum, auto
from http import HTTPMethod

from flask import Flask, Response, request

from maestro.routes.state_changed import handle_state_changed

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


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
