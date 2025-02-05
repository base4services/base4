import os
from typing import Optional, Any, Union
from redis.asyncio import Redis, ConnectionPool, StrictRedis
from redis.asyncio.connection import ConnectionError, TimeoutError
from redis.exceptions import RedisError
import fakeredis.aioredis
import json
import logging
from datetime import timedelta
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAsyncRedis(ABC):
    """Abstract base class defining the Redis interface"""

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def set(
            self,
            key: str,
            value: Any,
            expiration: Optional[Union[int, timedelta]] = None,
            nx: bool = False,
            xx: bool = False,
    ) -> bool:
        pass

    @abstractmethod
    async def flushall(self) -> None:
        pass

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    async def setex(self, name: str, time: int, value: any) -> bool:
        pass

    @abstractmethod
    async def delete_key(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        pass

    @abstractmethod
    async def lpush(self, key: str, *values: Any) -> int:
        pass

    @abstractmethod
    async def rpush(self, key: str, *values: Any) -> int:
        pass

    @abstractmethod
    async def lpop(self, key: str) -> Any:
        pass

    @abstractmethod
    async def rpop(self, key: str) -> Any:
        pass
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

class AsyncRedisFake(BaseAsyncRedis):
    """In-memory fake Redis implementation for testing"""

    def __init__(self, decode_responses: bool = True):
        self.client = fakeredis.aioredis.FakeRedis(decode_responses=decode_responses)

    async def connect(self) -> None:
        # FakeRedis doesn't need real connection
        pass

    async def disconnect(self) -> None:
        await self.client.aclose()

    async def set(
            self,
            key: str,
            value: Any,
            expiration: Optional[Union[int, timedelta]] = None,
            nx: bool = False,
            xx: bool = False,
    ) -> bool:
        if not isinstance(value, (str, int, float, bool)):
            value = json.dumps(value)

        result = await self.client.set(
            key,
            value,
            ex=expiration,
            nx=nx,
            xx=xx
        )
        return bool(result)

    async def get(self, key: str, default: Any = None) -> Any:
        value = await self.client.get(key)
        if value is None:
            return default

        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    async def setex(self, name: str, time: int, value: Any) -> bool:
        return await self.client.setex(name, time, value)

    async def delete_key(self, key: str) -> bool:
        result = await self.client.delete(key)
        return bool(result)

    async def exists(self, key: str) -> bool:
        result = await self.client.exists(key)
        return bool(result)

    async def increment(self, key: str, amount: int = 1) -> int:
        return await self.client.incrby(key, amount)

    async def lpush(self, key: str, *values: Any) -> int:
        serialized_values = [
            json.dumps(v) if not isinstance(v, (str, int, float, bool)) else v
            for v in values
        ]
        return await self.client.lpush(key, *serialized_values)

    async def rpush(self, key: str, *values: Any) -> int:
        serialized_values = [
            json.dumps(v) if not isinstance(v, (str, int, float, bool)) else v
            for v in values
        ]
        return await self.client.rpush(key, *serialized_values)

    async def lpop(self, key: str) -> Any:
        value = await self.client.lpop(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    async def rpop(self, key: str) -> Any:
        value = await self.client.rpop(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    async def flushall(self) -> None:
        """Additional method to clear all data - useful for testing"""
        await self.client.flushall()

def get_redis():


    if os.getenv('TEST_MODE', 'False').lower() == 'true':

        if hasattr(get_redis, 'fake_redis'):
            return get_redis.fake_redis

        get_redis.fake_redis = AsyncRedisFake()
        return get_redis.fake_redis

    return StrictRedis(decode_responses=False, host=os.getenv('DB_REDIS_HOST','localhost'), port=os.getenv('DB_REDIS_PORT'))
