from abc import ABC
from datetime import datetime
from typing import Any

from maestro.integrations.home_assistant.types import AttributeId, EntityId
from maestro.integrations.state_manager import StateManager


class EntityAttribute[T]:
    def __init__(self, attribute_type: type[T]) -> None:
        self.attribute_type = attribute_type

    def __set_name__(self, owner: type["Entity"], name: str) -> None:
        self.name = name

    def __get__(self, obj: "Entity", objtype: type["Entity"] | None = None) -> T:
        id = AttributeId(f"{obj.id}.{self.name}")
        value = obj.state_manager.get_cached_state(id)
        if not isinstance(value, self.attribute_type):
            raise TypeError(f"Type mismatch for cached attribute {id}")

        return value

    def __set__(self, obj: "Entity", value: T) -> None:
        entity_response = obj.state_manager.fetch_hass_entity(obj.id)
        if entity_response is None:
            raise ValueError(f"Failed to retrieve entity response for {obj.id}")

        entity_response.attributes[self.name] = value
        obj.state_manager.hass_client.set_entity(
            entity_id=obj.id,
            state=entity_response.state,
            attributes=entity_response.attributes,
        )


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

        if self.id.domain != type(self).__name__.lower():
            raise ValueError("Mismatch between entity domain and domain class")

    @property
    def state_manager(self) -> StateManager:
        """Lazy load the state manager only once it's needed"""
        self._state_manager = self._state_manager or StateManager()
        return self._state_manager

    @property
    def state(self) -> str:
        """Get the current state of the entity (always a string)"""
        state = self.state_manager.get_cached_state(self.id)
        if not isinstance(state, str):
            raise TypeError("Entity state must be a string")

        return state

    @state.setter
    def state(self, value: str) -> None:
        """Set the state of the entity"""
        entity_response = self.state_manager.fetch_hass_entity(self.id)
        if entity_response is None:
            raise ValueError(f"Failed to retrieve entity response for {self.id}")

        entity_response.state = value
        self.state_manager.hass_client.set_entity(
            entity_id=self.id,
            state=entity_response.state,
            attributes=entity_response.attributes,
        )

    def perform_action(self, action: str, **kwargs: Any) -> None:
        """Perform an action related to the entity"""
        response = self.state_manager.hass_client.perform_action(
            domain=self.id.domain,
            action=action,
            entity_id=self.id,
            **kwargs,
        )
        if len(response) > 1:
            raise ValueError("Unexpectedly received more than one EntityResponse from action call")
