import os
from typing import Optional, Any, Union
from redis.asyncio import Redis, ConnectionPool
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
    async def set_value(
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
    async def get_value(self, key: str, default: Any = None) -> Any:
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

class AsyncRedis(BaseAsyncRedis):
    """Real Redis implementation"""

    def __init__(
            self,
            host: str = "localhost",
            port: int = 6379,
            db: int = 0,
            password: Optional[str] = None,
            connection_timeout: int = 5,
            max_connections: int = 10,
            decode_responses: bool = True,
    ):
        self.connection_params = {
            "host": host,
            "port": port,
            "db": db,
            "password": password,
            "decode_responses": decode_responses,
            "socket_timeout": connection_timeout,
            "socket_connect_timeout": connection_timeout,
        }

        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None
        self.max_connections = max_connections

    async def flushall(self) -> None:
        await self.client.flushall()

    async def connect(self) -> None:
        try:
            if not self.pool:
                self.pool = ConnectionPool(
                    max_connections=self.max_connections,
                    **self.connection_params
                )

            if not self.client:
                self.client = Redis(connection_pool=self.pool)

            await self.client.ping()
            logger.info("Successfully connected to Redis")

        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Redis connection: {str(e)}")
            raise

    async def disconnect(self) -> None:
        try:
            if self.client:
                await self.client.close()
                self.client = None
            if self.pool:
                await self.pool.disconnect()
                self.pool = None
            logger.info("Successfully disconnected from Redis")
        except Exception as e:
            logger.error(f"Error during Redis disconnection: {str(e)}")
            raise

    async def set_value(
            self,
            key: str,
            value: Any,
            expiration: Optional[Union[int, timedelta]] = None,
            nx: bool = False,
            xx: bool = False,
    ) -> bool:
        try:
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
        except Exception as e:
            logger.error(f"Error setting value: {str(e)}")
            raise

    async def get_value(self, key: str, default: Any = None) -> Any:
        try:
            value = await self.client.get(key)
            if value is None:
                return default

            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value

        except Exception as e:
            logger.error(f"Error getting value: {str(e)}")
            raise

    async def delete_key(self, key: str) -> bool:
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting key: {str(e)}")
            raise

    async def exists(self, key: str) -> bool:
        try:
            result = await self.client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking existence: {str(e)}")
            raise

    async def increment(self, key: str, amount: int = 1) -> int:
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing value: {str(e)}")
            raise

    async def lpush(self, key: str, *values: Any) -> int:
        try:
            serialized_values = [
                json.dumps(v) if not isinstance(v, (str, int, float, bool)) else v
                for v in values
            ]
            return await self.client.lpush(key, *serialized_values)
        except Exception as e:
            logger.error(f"Error pushing to list left: {str(e)}")
            raise

    async def rpush(self, key: str, *values: Any) -> int:
        try:
            serialized_values = [
                json.dumps(v) if not isinstance(v, (str, int, float, bool)) else v
                for v in values
            ]
            return await self.client.rpush(key, *serialized_values)
        except Exception as e:
            logger.error(f"Error pushing to list right: {str(e)}")
            raise

    async def lpop(self, key: str) -> Any:
        try:
            value = await self.client.lpop(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        except Exception as e:
            logger.error(f"Error popping from list left: {str(e)}")
            raise

    async def rpop(self, key: str) -> Any:
        try:
            value = await self.client.rpop(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        except Exception as e:
            logger.error(f"Error popping from list right: {str(e)}")
            raise

class AsyncRedisFake(BaseAsyncRedis):
    """In-memory fake Redis implementation for testing"""

    def __init__(self, decode_responses: bool = True):
        self.client = fakeredis.aioredis.FakeRedis(decode_responses=decode_responses)

    async def connect(self) -> None:
        # FakeRedis doesn't need real connection
        pass

    async def disconnect(self) -> None:
        await self.client.close()

    async def set_value(
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

    async def get_value(self, key: str, default: Any = None) -> Any:
        value = await self.client.get(key)
        if value is None:
            return default

        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

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

    return AsyncRedis()
