import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum

import redis

from maestro.config import REDIS_HOST, REDIS_PORT
from maestro.utils.dates import IntervalSeconds, resolve_timestamp


class CachePrefix(StrEnum):
    STATE = "STATE"
    REGISTERED = "REGISTERED"


@dataclass
class CachedValue:
    value: str
    type: str


CachedValueT = str | int | float | dict | list | bool | datetime


state_encoder_map: dict[type, Callable[[CachedValueT], str]] = {
    str: lambda x: str(x),
    int: lambda x: str(x),
    float: lambda x: str(x),
    dict: lambda x: json.dumps(x),
    list: lambda x: json.dumps(x),
    bool: lambda x: str(x),
    datetime: lambda x: x.isoformat() if isinstance(x, datetime) else "",
}
state_decoder_map: dict[str, Callable[[str], CachedValueT]] = {
    str.__name__: lambda x: str(x),
    int.__name__: lambda x: int(x),
    float.__name__: lambda x: float(x),
    dict.__name__: lambda x: json.loads(x) if isinstance(x, str) else dict(x),
    list.__name__: lambda x: json.loads(x) if isinstance(x, str) else list(x),
    bool.__name__: lambda x: x.lower() == "true",
    datetime.__name__: lambda x: resolve_timestamp(x),
}


class RedisClient:
    """Client for interacting with Redis"""

    def __init__(self) -> None:
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    def check_health(self) -> bool:
        """Check if Redis is accessible and healthy"""
        try:
            result = self.client.ping()
            if not isinstance(result, bool):
                raise TypeError(f"Expected `bool` but got {type(result).__name__}")
            return result
        except redis.RedisError:
            return False

    def get(self, key: str) -> str | None:
        """Get a string value by key"""
        result = self.client.get(key)
        if not isinstance(result, (str | type(None))):
            raise TypeError(f"Expected `str | None` but got {type(result).__name__}")
        return result

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = IntervalSeconds.ONE_HOUR,
    ) -> str | None:
        """Set a string value with optional expiration in seconds"""
        ex = int(ttl_seconds) if isinstance(ttl_seconds, IntEnum) else ttl_seconds

        old_value = self.client.set(name=key, value=value, ex=ex, get=True)

        if not isinstance(old_value, (str | type(None))):
            raise TypeError(f"Expected `str | None` but got {type(old_value).__name__}")
        return old_value

    def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns number of keys deleted"""
        if not keys:
            return 0
        keys_deleted = self.client.delete(*keys)
        if not isinstance(keys_deleted, int):
            raise TypeError(f"Expected `int` but got {type(keys_deleted).__name__}")
        return keys_deleted

    def exists(self, *keys: str) -> int:
        """Check if a key exists"""
        result = self.client.exists(*keys)
        if not isinstance(result, int):
            raise TypeError(f"Expected `int` but got {type(result).__name__}")
        return result

    def get_keys(self, pattern: str | None = None) -> list[str]:
        """Returns a list of keys, optionally filtered by pattern"""
        keys: list[str] = []
        cursor = None

        while cursor != 0:
            if cursor is None:
                cursor = 0
            result = self.client.scan(cursor=cursor, match=pattern)
            if not isinstance(result, tuple):
                raise TypeError(f"Expected `tuple` but got {type(result).__name__}")
            cursor, new_keys = result
            keys.extend(new_keys)

        return keys

    @classmethod
    def build_key(cls, *parts: str) -> str:
        """Builds a redis key from provided args"""
        return ":".join(parts)

    @classmethod
    def encode_cached_state(cls, value: CachedValueT) -> str:
        for encoder_type in state_encoder_map:
            if isinstance(value, encoder_type):
                break
        else:
            raise TypeError(f"No state encoder exists for type {encoder_type.__name__}")

        encoded_state = CachedValue(
            value=state_encoder_map[encoder_type](value),
            type=encoder_type.__name__,
        )

        return json.dumps(
            {
                "value": encoded_state.value,
                "type": encoded_state.type,
            }
        )

    @classmethod
    def decode_cached_state(cls, cached_state: CachedValue) -> CachedValueT:
        if cached_state.type not in state_decoder_map:
            raise TypeError(f"No state decoder exists for type {cached_state.type}")

        decoder_function = state_decoder_map[cached_state.type]

        return decoder_function(cached_state.value)
