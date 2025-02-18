import os
from typing import Optional, Any, Union
from redis.asyncio import Redis, ConnectionPool, StrictRedis
from redis.asyncio.connection import ConnectionError, TimeoutError
from redis.exceptions import RedisError
import fakeredis.aioredis
import json
import logging
from datetime import timedelta, datetime
from abc import ABC, abstractmethod
import redis

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

    return StrictRedis(decode_responses=False, host=os.getenv('DB_REDIS_HOST', 'localhost'), port=os.getenv('DB_REDIS_PORT', 6379))


def get_sync_redis():

    if hasattr(get_sync_redis, 'redis'):
        return get_sync_redis.redis

    if os.getenv('TEST_MODE', 'False').lower() == 'true':
        get_sync_redis.redis = fakeredis.FakeRedis()
        return get_sync_redis.redis

    get_sync_redis.redis = redis.Redis(host=os.getenv('DB_REDIS_HOST', 'localhost'), port=os.getenv('DB_REDIS_PORT', 6379))
    return get_sync_redis.redis


class RedisLoggingHandler(logging.Handler):
    def __init__(self, **kwargs):
        super().__init__()
        self.queue_name = kwargs.get('queue_name')
        # self.redis: Optional[redis.Redis] = None
        #
        # self.redis_class = redis.Redis
        #
        # if os.getenv('TEST_MODE', 'False').lower() == 'true':
        #     if hasattr(get_redis, 'fake_redis'):
        #         self.redis_class =  fakeredis.FakeRedis

        self.redis = get_sync_redis()

        self._connect()

    def _connect(self):
        try:
            # self.redis = self.redis_class(host=os.getenv('DB_REDIS_HOST', 'localhost'), port=os.getenv('DB_REDIS_PORT', 6379))
            self.redis.ping()  # Test connection
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {e}")
            self.redis = None

    def emit(self, record):
        if not self.redis:
            return

        message = None
        if record.name == 'flows':
            spl = record.message.split('|')
            message = {
                'id_tenant': spl[0] if spl[0] not in (None,'None') else None,
                'id_user': spl[1] if spl[1] not in (None,'None') else None,
                'instance': spl[2] if spl[2] not in (None,'None') else None,
                'id_instance': spl[3] if spl[3] not in (None,'None') else None,
                'message': spl[4] if spl[4] not in (None,'None') else None,
                'data': json.loads(spl[5]) if spl[5] not in (None,'None') else None
            }
        else:
            message = record.message


        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'message': message,
                'logger': record.name,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }

            # Use Redis pipeline for atomic operations
            with self.redis.pipeline() as pipe:
                # Push the new log entry to the right of the list
                pipe.rpush(self.queue_name, json.dumps(log_entry))

                # # Trim the list if it exceeds max_length
                # if self.max_length:
                #     pipe.ltrim(self.queue_name, -self.max_length, -1)

                pipe.execute()

        except Exception as e:
            self.handleError(record)

