from flask import Response, jsonify, request
from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import FiredEvent
from maestro.integrations.home_assistant.users import user_accounts
from maestro.triggers.event_fired import EventFiredTriggerManager
from maestro.utils.dates import resolve_timestamp

log = get_logger()


def handle_event_fired() -> tuple[Response, int]:
    request_body = request.get_json() or {}

    user_id = user_accounts.get(request_body["user_id"]) or request_body["user_id"]
    if not isinstance(user_id, str) and user_id is not None:
        raise TypeError(f"Unexpected type receieved for user_id: {type(user_id)}")

    fired_event = FiredEvent(
        timestamp=resolve_timestamp(request_body["timestamp"] or ""),
        time_fired=resolve_timestamp(request_body["time_fired"] or ""),
        type=request_body["event_type"],
        data=request_body["data"],
        user_id=user_id,
    )

    EventFiredTriggerManager.fire_triggers(fired_event)

    return jsonify({"status": "success"}), 200
