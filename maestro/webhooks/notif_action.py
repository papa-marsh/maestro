from flask import Response, jsonify
from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import NotifActionEvent
from maestro.triggers.notif_action import NotifActionTriggerManager
from maestro.utils.dates import resolve_timestamp

log = get_logger()


def handle_notif_action(request_body: dict) -> tuple[Response, int]:
    user_id = str(request_body["user_id"]) if request_body["user_id"] is not None else None

    ios_notif_action = NotifActionEvent(
        timestamp=resolve_timestamp(request_body["timestamp"] or ""),
        time_fired=resolve_timestamp(request_body["time_fired"] or ""),
        type=request_body["event_type"],
        data=request_body["data"],
        user_id=user_id,
        name=request_body["data"]["actionName"],
        action_data=request_body["data"]["action_data"],
        device_id=request_body["data"]["sourceDeviceID"],
        device_name=request_body["data"]["sourceDeviceName"],
    )

    NotifActionTriggerManager.fire_triggers(ios_notif_action)

    return jsonify({"status": "success"}), 200
