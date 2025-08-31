from abc import ABC
from datetime import datetime
from typing import Any

from maestro.domains.domain import Domain
from maestro.integrations.state_manager import StateManager


class EntityAttribute[T]:
    def __init__(self, attribute_type: type[T]) -> None:
        self.attribute_type = attribute_type

    def __set_name__(self, owner: type["Entity"], name: str) -> None:
        self.name = name

    def __get__(self, obj: "Entity", objtype: type["Entity"] | None = None) -> T:
        id = f"{obj.entity_id}.{self.name}"
        value = obj.state_manager.get_cached_state(id)
        if not isinstance(value, self.attribute_type):
            raise TypeError(f"Type mismatch for cached attribute {id}")

        return value

    def __set__(self, obj: "Entity", value: T) -> None: ...


class Entity(ABC):
    state_manager: StateManager
    domain: Domain
    name: str

    friendly_name = EntityAttribute(str)
    last_changed = EntityAttribute(datetime)
    last_updated = EntityAttribute(datetime)

    def __init__(
        self,
        entity_id: str,
        state_manager: StateManager | None = None,
    ) -> None:
        entity_parts = entity_id.split(".")
        if len(entity_parts) != 2:
            raise ValueError("Entity string must adhere to `<domain>.<name`> format")

        self.entity_id = entity_id
        self.domain = Domain(entity_parts[0])
        self.name = entity_parts[1]
        if self.domain != type(self).__name__.lower():
            raise ValueError("Mismatch between entity domain and domain class")

        self.state_manager = state_manager or StateManager()

    @property
    def state(self) -> str:
        """Get the current state of the entity (always a string)"""
        state = self.state_manager.get_cached_state(self.entity_id)
        if not isinstance(state, str):
            raise TypeError("Entity state must be a string")

        return state

    @state.setter
    def state(self, value: str) -> None:
        """Set the state of the entity"""
        ...

    def perform_action(self, action: str, **kwargs: Any) -> dict:
        """Perform an action related to the entity"""
        ...
