from maestro.config import DOMAIN_IGNORE_LIST
from maestro.handlers.types import EventTypeName
from maestro.integrations.home_assistant.types import (
    EntityData,
    EntityId,
    StateChangeEvent,
    WebSocketEvent,
)
from maestro.integrations.state_manager import StateManager
from maestro.triggers.state_change import StateChangeTriggerManager
from maestro.utils.dates import resolve_timestamp
from maestro.utils.exceptions import MalformedResponseError
from maestro.utils.logging import log


def resolve_entity_state_data(raw_entity_dict: dict) -> EntityData:
    try:
        attributes = raw_entity_dict["attributes"]
        attributes["last_changed"] = resolve_timestamp(raw_entity_dict["last_changed"])
        attributes["last_updated"] = resolve_timestamp(raw_entity_dict["last_updated"])

        return EntityData(
            entity_id=EntityId(raw_entity_dict["entity_id"]),
            state=str(raw_entity_dict["state"]),
            attributes=attributes,
        )
    except Exception as e:
        raise MalformedResponseError("Failed to resolve entity data from state change") from e


def handle_state_changed(event: WebSocketEvent) -> None:
    state_manager = StateManager()

    entity_id = EntityId(event.data["entity_id"])
    if entity_id.domain in DOMAIN_IGNORE_LIST:
        log.debug("Skipping state change for domain in ignore list", entity_id=entity_id)
        return

    old_raw_data: dict | None = event.data.get("old_state")
    new_raw_data: dict | None = event.data.get("new_state")

    if old_raw_data is None and new_raw_data is None:
        raise MalformedResponseError("State change received with null data for both old and new")

    if old_raw_data is not None:
        old_data = resolve_entity_state_data(old_raw_data)
        if new_raw_data is None:
            state_manager.delete_cached_entity(entity_id)
            log.info("State deletion cached", entity_id=entity_id, old_state=old_data.state)
            return

    if new_raw_data is not None:
        new_data = resolve_entity_state_data(new_raw_data)
        if old_raw_data is None:
            state_manager.cache_entity(new_data)
            log.info("State creation cached", entity_id=entity_id, new_state=new_data.state)
            return

    log.debug(
        "Processing state change",
        entity_id=entity_id,
        old_state=old_data.state,
        new_state=new_data.state,
    )

    state_change = StateChangeEvent(
        time_fired=event.time_fired,
        type=EventTypeName.STATE_CHANGED,
        data=event.data,
        user_id=event.context.user_id,
        entity_id=entity_id,
        old=old_data,
        new=new_data,
    )
    state_change.new.attributes["previous_state"] = old_data.state
    changes = {}

    if old_data.state != new_data.state:
        changes["state"] = (state_change.old.state, state_change.new.state)

    custom_attributes = ["previous_state", "last_changed", "last_updated"]
    for attr in state_change.old.attributes.keys() | state_change.new.attributes.keys():
        old_attr_data = state_change.old.attributes.get(attr)
        new_attr_data = state_change.new.attributes.get(attr)
        if old_attr_data != new_attr_data and attr not in custom_attributes:
            changes[attr] = (str(old_attr_data), str(new_attr_data))
    log.debug("Caching state change", entity_id=state_change.entity_id, changes=changes)

    state_manager.cache_entity(state_change.new)

    if new_data.state == old_data.state:
        log.debug(
            "Skipping triggers for unchanged state",
            entity_id=entity_id,
            state=new_data.state,
        )
        return

    StateChangeTriggerManager.fire_triggers(state_change)
