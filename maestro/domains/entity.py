from abc import ABC
from datetime import datetime
from enum import StrEnum, auto
from typing import Any


class Domain(StrEnum):
    CALENDAR = auto()
    CLIMATE = auto()
    COVER = auto()
    FAN = auto()
    INPUT_BOOLEAN = auto()
    LIGHT = auto()
    LOCK = auto()
    MEDIA_PLAYER = auto()
    SWITCH = auto()


class EntityAttribute[T]:
    def __set_name__(self, owner: type["Entity"], name: str) -> None:
        self.name = name

    def __get__(self, obj: "Entity", objtype: type["Entity"] | None = None) -> T: ...  # type:ignore[empty-body]

    def __set__(self, obj: "Entity", value: T) -> None: ...


class Entity(ABC):
    domain: Domain
    name: str

    friendly_name = EntityAttribute[str]()

    def __init__(self, entity_id: str) -> None:
        entity_parts = entity_id.split(".")
        if len(entity_parts) != 2:
            raise ValueError("Entity string must adhere to `<domain>.<name`> format")

        self.entity_id = entity_id
        self.domain = Domain(entity_parts[0])
        self.name = entity_parts[1]
        if self.domain != type(self).__name__.lower():
            raise ValueError("Mismatch between entity domain and domain class")

    @property
    def state(self) -> str:  # type:ignore[empty-body]
        """Get the current state of the entity"""
        ...

    @state.setter
    def state(self, value: str) -> None:
        """Set the state of the entity"""
        ...

    def get_attribute(self, attribute_name: str) -> Any:
        """Get the current value of one of the entity's attributes"""
        ...

    def set_attribute(self, attribute_name: str, value: Any) -> None:
        """Set one of the entity's attributes"""
        ...

    @property
    def last_changed(self) -> datetime:  # type:ignore[empty-body]
        """Get the datetime when the entity state last changed"""
        ...

    def perform_action(self, action: str, **kwargs: Any) -> dict:  # type:ignore[empty-body]
        """Perform an action related to the entity"""
        ...
