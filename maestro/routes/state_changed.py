from flask import Response, jsonify, request

from maestro.integrations.home_assistant import StateChangeEvent
from maestro.integrations.state_manager import StateManager
from maestro.utils.dates import resolve_timestamp


def handle_state_changed() -> tuple[Response, int]:
    request_body = request.get_json() or {}
    state_manager = StateManager()

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

    state_manager.cache_state_change(state_change_data)

    return jsonify({"status": "success"}), 200
