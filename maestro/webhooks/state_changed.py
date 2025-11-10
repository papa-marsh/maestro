from flask import Response, jsonify

from maestro.config import DOMAIN_IGNORE_LIST
from maestro.integrations.home_assistant.types import EntityData, EntityId, StateChangeEvent
from maestro.integrations.state_manager import StateManager
from maestro.triggers.state_change import StateChangeTriggerManager
from maestro.utils.dates import resolve_timestamp
from maestro.utils.logger import log


def handle_state_changed(request_body: dict) -> tuple[Response, int]:
    state_manager = StateManager()
    entity_id_str = str(request_body["entity_id"])

    log.info(
        "Processing state change",
        entity_id=entity_id_str,
        old_state=request_body.get("old_state"),
        new_state=request_body.get("new_state"),
    )

    if entity_id_str.split(".")[0] in DOMAIN_IGNORE_LIST:
        log.info("Skipping entity for domain in ignore list", entity_id=entity_id_str)
        return jsonify({"status": "success"}), 200

    entity_id = EntityId(entity_id_str)
    old_state = str(request_body["old_state"]) if request_body["old_state"] is not None else None
    new_state = str(request_body["new_state"]) if request_body["new_state"] is not None else None
    last_changed = resolve_timestamp(request_body["time_fired"] or "")
    last_updated = resolve_timestamp(request_body["timestamp"] or "")

    if old_state is not None:
        old_data = EntityData(
            entity_id=EntityId(entity_id_str),
            state=old_state,
            attributes=request_body["old_attributes"] or {},
        )
    if new_state is not None:
        new_data = EntityData(
            entity_id=EntityId(entity_id_str),
            state=new_state,
            attributes=request_body["new_attributes"] or {},
        )
        new_data.attributes["last_changed"] = last_changed
        new_data.attributes["last_updated"] = last_updated

    if not old_state and not new_state:
        return jsonify({"status": "failure"}), 400

    if old_state is None:
        state_manager.cache_entity(new_data)
        log.info("State creation cached", entity_id=entity_id, new_state=new_data.state)
        return jsonify({"status": "success"}), 200

    if new_state is None:
        state_manager.delete_cached_entity(entity_id)
        log.info("State deletion cached", entity_id=entity_id, old_state=old_data.state)
        return jsonify({"status": "success"}), 200

    if new_state == "unavailable":
        log.warning(
            "Entity state changed to unavailable/unknown. Skipping cache.",
            entity_id=entity_id,
            old_state=old_state,
            new_state=new_state,
        )
        return jsonify({"status": "success"}), 200

    if old_state == "unavailable":
        log.warning(
            "Entity state is no longer unavailable/unknown",
            entity_id=entity_id,
            old_state=old_state,
            new_state=new_state,
        )

    state_change = StateChangeEvent(
        timestamp=last_updated,
        time_fired=last_changed,
        entity_id=EntityId(entity_id),
        old=old_data,
        new=new_data,
    )
    state_change.new.attributes["previous_state"] = old_state

    changes = {"state": (state_change.old.state, state_change.new.state)}
    custom_attributes = ["previous_state", "last_changed", "last_updated"]
    for attr in state_change.old.attributes.keys() | state_change.new.attributes.keys():
        old_attr_data = state_change.old.attributes.get(attr)
        new_attr_data = state_change.new.attributes.get(attr)
        if old_attr_data != new_attr_data and attr not in custom_attributes:
            changes[attr] = (str(old_attr_data), str(new_attr_data))
    log.info("Caching state change", entity_id=state_change.entity_id, changes=changes)

    state_manager.cache_entity(state_change.new)

    if new_state == old_state:
        log.info("Skipping triggers for unchanged state", entity_id=entity_id, state=new_state)
    else:
        StateChangeTriggerManager.fire_triggers(state_change)

    return jsonify({"status": "success"}), 200
