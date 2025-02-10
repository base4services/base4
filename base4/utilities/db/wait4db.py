import redis
import time
import asyncpg
import os
import asyncio

import logging
log = logging.getLogger()

async def check_postgres_db():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_POSTGRES_HOST'),
            database="template1",
            user=os.getenv("DB_POSTGRES_USER"),
            password=os.getenv("DB_POSTGRES_PASSWORD"),
            port=os.getenv("DB_POSTGRES_PORT")
        )
        await conn.fetch('''SELECT now()''')
        await conn.close()
    except Exception as e:
        log.critical(f"Failed to connect to postgres: host={os.getenv('DB_POSTGRES_HOST')}, port={os.getenv('DB_POSTGRES_PORT')}, user={os.getenv('DB_POSTGRES_USER')}")
        return False

    return True


async def check_redis_db():
    try:
        r = redis.Redis(host=os.getenv('DB_REDIS_HOST'), port=int(os.getenv('DB_REDIS_PORT')))
        r.ping()
    except Exception as e:
        log.critical(f"Failed to connect to redis: host={os.getenv('DB_REDIS_HOST')}, port={int(os.getenv('DB_REDIS_PORT'))}")
        return False

    return True


async def wait4(check_fn):
    ts = 0
    start = time.time()

    while True:

        if await check_fn():
            log.info(f"Successfully connected to database using {check_fn}")
            return True

        time.sleep(ts)
        ts += 0.1
        if ts > 2:
            ts == 2

        print(check_fn, time.time() - start)

        if time.time() - start > 60:
            return False


async def wait4postgres():
    log.info('Wait4Postgres')
    return await wait4(check_postgres_db)


async def wait4redis():
    log.info('Wait4Redis')
    return await wait4(check_redis_db)


async def wait4db():
    log.info('Wait4DB')
    return await wait4postgres() and await wait4redis()


if __name__ == '__main__':
    asyncio.run(wait4db())





