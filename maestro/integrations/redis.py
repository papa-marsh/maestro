import redis

from maestro.config import REDIS_HOST, REDIS_PORT

TWO_WEEKS_IN_SEC = 14 * 24 * 60 * 60


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
                raise TypeError(f"Expected `bool` from redis `ping` but got {type(result)}")
            return result
        except redis.RedisError:
            return False

    def get(self, key: str) -> str | None:
        """Get a string value by key"""
        result = self.client.get(key)
        if not isinstance(result, (str | type(None))):
            raise TypeError(f"Expected `str | None` from redis `get` but got {type(result)}")
        return result

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = TWO_WEEKS_IN_SEC,
    ) -> str | None:
        """Set a string value with optional expiration in seconds"""
        old_value = self.client.set(name=key, value=value, ex=ttl_seconds, get=True)
        if not isinstance(old_value, (str | type(None))):
            raise TypeError(f"Expected `str | None` from redis `set` but got {type(old_value)}")
        return old_value

    def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns number of keys deleted"""
        keys_deleted = self.client.delete(*keys)
        if not isinstance(keys_deleted, int):
            raise TypeError(f"Expected `int` from redis delete but got {type(keys_deleted)}")
        return keys_deleted

    def exists(self, *keys: str) -> int:
        """Check if a key exists"""
        result = self.client.exists(*keys)
        if not isinstance(result, int):
            raise TypeError(f"Expected `int` from redis `exists` but got {type(result)}")
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
                raise TypeError
            cursor, new_keys = result
            keys.extend(new_keys)

        return keys

    @classmethod
    def build_key(cls, *parts: str) -> str:
        """Builds a redis key from provided args"""
        return ":".join(parts)
