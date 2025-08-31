import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from maestro.integrations.home_assistant import HomeAssistantClient
from maestro.integrations.redis import RedisClient

STATE_CACHE_PREFIX = "STATE"


@dataclass
class CachedState:
    value: str
    type: str


CachedStateValueT = str | int | float | dict | datetime | None

state_encoder_map: dict[str, Callable[[CachedStateValueT], str]] = {
    str.__name__: lambda x: str(x),
    int.__name__: lambda x: str(x),
    float.__name__: lambda x: str(x),
    dict.__name__: lambda x: json.dumps(x),
    datetime.__name__: lambda x: x.isoformat() if isinstance(x, datetime) else "",
    type(None).__name__: lambda _: "",
}
state_decoder_map: dict[str, Callable[[str], CachedStateValueT]] = {
    str.__name__: lambda x: str(x),
    int.__name__: lambda x: int(x),
    float.__name__: lambda x: float(x),
    dict.__name__: lambda x: json.loads(x) if isinstance(x, str) else dict(x),
    datetime.__name__: lambda x: datetime.fromisoformat(x),
    type(None).__name__: lambda _: None,
}

attribute_ignore_list = {
    "editable",
    "device_class",
    "supported_features",
    "entity_picture",
    "editable",
    "icon",
    "attribution",
}


class StateManager:
    home_assistant_client: HomeAssistantClient
    redis_client: RedisClient

    def __init__(
        self,
        home_assistant_client: HomeAssistantClient | None = None,
        redis_client: RedisClient | None = None,
    ) -> None:
        self.home_assistant_client = home_assistant_client or HomeAssistantClient()
        self.redis_client = redis_client or RedisClient()

    def get_cached_state(self, id: str) -> CachedStateValueT:
        """Retrieve an entity's state or attribute value from Redis"""
        parts = id.split(".")
        if len(parts) not in [2, 3]:
            raise ValueError("Invalid format receieved for state/attribute name")
        key = RedisClient.build_key(STATE_CACHE_PREFIX, *parts)

        encoded_value = self.redis_client.get(key)
        if encoded_value is None:
            return None

        data = json.loads(encoded_value)
        cached_state = CachedState(value=data["value"], type=data["type"])

        return self.decode_cached_state(cached_state)

    def set_cached_state(self, id: str, value: CachedStateValueT) -> CachedStateValueT:
        """Stores an entity's state or attribute value in Redis along with its type"""
        parts = id.split(".")
        if len(parts) not in [2, 3]:
            raise ValueError("Invalid format receieved for state/attribute name")
        if len(parts) == 2 and not isinstance(value, str):
            raise TypeError("State value must be a string")

        key = RedisClient.build_key(STATE_CACHE_PREFIX, *parts)
        encoded_value = self.encode_cached_state(value)

        old_encoded_value = self.redis_client.set(key, encoded_value)

        if old_encoded_value is None:
            return None

        old_data = json.loads(old_encoded_value)
        old_cached_state = CachedState(value=old_data["value"], type=old_data["type"])

        return self.decode_cached_state(old_cached_state)

    def refresh_cached_state(self, entity_id: str) -> None:
        if entity_id.count(".") != 1:
            raise ValueError("Refreshing cached state requires a valid entity ID")
        entity_state = self.home_assistant_client.get_entity_state(entity_id)
        if not entity_state:
            raise ValueError(f"Failed to retrieve an entity state for {entity_id}")

        self.set_cached_state(entity_id, entity_state.state)
        self.set_cached_state(f"{entity_id}.{'last_changed'}", entity_state.last_changed)
        self.set_cached_state(f"{entity_id}.{'last_updated'}", entity_state.last_updated)
        for attribute, value in entity_state.attributes.items():
            if attribute in attribute_ignore_list:
                continue
            self.set_cached_state(f"{entity_id}.{attribute}", value)

    @classmethod
    def encode_cached_state(cls, value: CachedStateValueT) -> str:
        type_name = type(value).__name__
        if type_name not in state_encoder_map:
            raise TypeError(f"No state encoder exists for type {type_name}")

        encoded_state = CachedState(
            value=state_encoder_map[type_name](value),
            type=type_name,
        )

        return json.dumps(
            {
                "value": encoded_state.value,
                "type": encoded_state.type,
            }
        )

    @classmethod
    def decode_cached_state(cls, cached_state: CachedState) -> CachedStateValueT:
        if cached_state.type not in state_decoder_map:
            raise TypeError(f"No state decoder exists for type {cached_state.type}")

        decoder_function = state_decoder_map[cached_state.type]

        return decoder_function(cached_state.value)
