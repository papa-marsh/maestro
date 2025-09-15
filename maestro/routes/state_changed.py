from typing import Any

from flask import Response, jsonify, request
from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent
from maestro.integrations.state_manager import StateManager
from maestro.triggers.state_change import StateChangeTriggerManager
from maestro.utils.dates import resolve_timestamp

log = get_logger()


def handle_state_changed() -> tuple[Response, int]:
    request_body = request.get_json() or {}
    state_manager = StateManager()

    old_state = None if request_body["old_state"] is None else str(request_body["old_state"])
    new_state = None if request_body["new_state"] is None else str(request_body["new_state"])

    state_change = StateChangeEvent(
        timestamp=resolve_timestamp(request_body["timestamp"] or ""),
        time_fired=resolve_timestamp(request_body["time_fired"] or ""),
        event_type=request_body["event_type"] or "",
        entity_id=EntityId(request_body["entity_id"] or ""),
        old_state=old_state,
        new_state=new_state,
        old_attributes=request_body["old_attributes"] or {},
        new_attributes=request_body["new_attributes"] or {},
    )

    changes: dict[str, tuple[Any, Any]] = {}
    if state_change.old_state != state_change.new_state:
        changes["state"] = (state_change.old_state, state_change.new_state)
    for attr in state_change.old_attributes.keys() | state_change.new_attributes.keys():
        old = state_change.old_attributes.get(attr)
        new = state_change.new_attributes.get(attr)
        if old != new:
            changes[attr] = (old, new)

    state_change.new_attributes["last_changed"] = state_change.time_fired
    state_change.new_attributes["last_updated"] = state_change.timestamp
    state_change.new_attributes["previous_state"] = state_change.old_state

    state_manager.cache_state_change(state_change)
    log.info("State change cached", entity_id=state_change.entity_id, changes=changes)

    StateChangeTriggerManager.resolve_triggers(state_change)

    return jsonify({"status": "success"}), 200
