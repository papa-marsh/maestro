from dataclasses import dataclass
from datetime import datetime

from flask import Response, current_app, jsonify, request

from maestro.utils.dates import resolve_timestamp


@dataclass
class StateChangeEvent:
    timestamp: datetime
    time_fired: datetime
    event_type: str
    entity_id: str
    old_state: str
    new_state: str
    old_attributes: dict
    new_attributes: dict


def handle_state_changed() -> tuple[Response, int]:
    request_body = request.get_json() or {}

    state_change_data = StateChangeEvent(
        timestamp=resolve_timestamp(request_body["timestamp"] or ""),
        time_fired=resolve_timestamp(request_body["time_fired"] or ""),
        event_type=request_body["event_type"] or "",
        entity_id=request_body["entity_id"] or "",
        old_state=str(request_body["old_state"]) or "",
        new_state=str(request_body["new_state"]) or "",
        old_attributes=request_body["old_attributes"] or {},
        new_attributes=request_body["new_attributes"] or {},
    )

    return jsonify({"status": "success"}), 200
