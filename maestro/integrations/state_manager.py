from maestro.integrations.home_assistant import HomeAssistantClient
from maestro.integrations.redis import RedisClient

STATE_CACHE_PREFIX = "STATE"


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

    def get_cached_state(self, name: str) -> str | None:
        """Retrieve an entity's state or attribute value from Redis"""
        parts = name.split(".")
        if len(parts) not in [2, 3]:
            raise ValueError("Invalid format receieved for state/attribute name")
        key = RedisClient.build_key(STATE_CACHE_PREFIX, *parts)

        return self.redis_client.get(key)

    def set_cached_state(self, name: str, value: str) -> str | None:
        """Stores an entity's state or attribute value in Redis"""
        parts = name.split(".")
        if len(parts) not in [2, 3]:
            raise ValueError("Invalid format receieved for state/attribute name")
        key = RedisClient.build_key(STATE_CACHE_PREFIX, *parts)

        return self.redis_client.set(key, value)
