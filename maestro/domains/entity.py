from abc import ABC
from datetime import datetime
from typing import Any, cast

from maestro.integrations.home_assistant.types import AttributeId, EntityId
from maestro.integrations.state_manager import StateManager
from maestro.utils.exceptions import EntityConfigurationError, MalformedResponseError
from maestro.utils.internal import test_mode_active

ON = "on"
OFF = "off"
HOME = "home"
AWAY = "not_home"


class EntityAttribute[T: (str, int, float, dict, list, bool, datetime)]:
    def __init__(self, attribute_type: type[T]) -> None:
        self.attribute_type: type[T] = attribute_type

    def __set_name__(self, owner: type["Entity"], name: str) -> None:
        self.name = name

    def __get__(self, obj: "Entity", objtype: type["Entity"] | None = None) -> T:
        attribute_id = AttributeId(f"{obj.id}.{self.name}")
        value = obj.state_manager.get_attribute_state(
            attribute_id=attribute_id,
            expected_type=self.attribute_type,
        )

        return cast(T, value)

    def __set__(self, obj: "Entity", value: T) -> None:
        entity_response = obj.state_manager.fetch_hass_entity(obj.id)

        entity_response.attributes[self.name] = value
        entity_data, _ = obj.state_manager.hass_client.set_entity(
            entity_id=obj.id,
            state=entity_response.state,
            attributes=entity_response.attributes,
        )
        obj.state_manager.cache_entity(entity_data)


class Entity(ABC):
    id: EntityId

    friendly_name = EntityAttribute(str)
    last_changed = EntityAttribute(datetime)
    last_updated = EntityAttribute(datetime)
    previous_state = EntityAttribute(str)

    def __init__(
        self,
        entity_id: str | EntityId,
        state_manager: StateManager | None = None,
    ) -> None:
        self.id = EntityId(entity_id) if isinstance(entity_id, str) else entity_id
        self._state_manager = state_manager

        valid_classes = {c.__name__ for c in type(self).__mro__ if c not in [Entity, ABC, object]}
        if self.id.domain_class_name not in valid_classes:
            raise EntityConfigurationError("Mismatch between entity domain and domain class")

    @property
    def state_manager(self) -> StateManager:
        """Lazy load the state manager for this entity"""
        if test_mode_active():
            return StateManager()

        self._state_manager = self._state_manager or StateManager()
        return self._state_manager

    def __getstate__(self) -> dict[str, Any]:
        """Exclude _state_manager from pickling to avoid serializing locks"""
        state = self.__dict__.copy()
        state["_state_manager"] = None
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore instance from pickled state, allowing lazy re-init of state_manager"""
        self.__dict__.update(state)

    @property
    def state(self) -> str:
        """Get the current state of the entity (always a string)"""
        return self.state_manager.get_entity_state(self.id)

    @state.setter
    def state(self, value: str) -> None:
        """Set the state of the entity"""
        entity_response = self.state_manager.fetch_hass_entity(self.id)

        entity_response.state = value
        entity_data, _ = self.state_manager.hass_client.set_entity(
            entity_id=self.id,
            state=entity_response.state,
            attributes=entity_response.attributes,
        )
        self.state_manager.cache_entity(entity_data)

    def perform_action(self, action: str, **kwargs: Any) -> None:
        """Perform an action related to the entity"""
        response = self.state_manager.hass_client.perform_action(
            domain=self.id.domain,
            action=action,
            entity_id=self.id,
            **kwargs,
        )
        if len(response) > 1:
            raise MalformedResponseError("Received more than one EntityData from action call")
