import asyncio
import os
from contextlib import asynccontextmanager
from typing import AnyStr, Dict, List, Optional

import asyncpg
import pydash
import yaml
from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from tortoise import Tortoise

from base4.schemas import DatabaseConfig
from base4.utilities.db.base import TORTOISE_ORM

current_file_path = os.path.abspath(os.path.dirname(__file__))

_test: Optional[AnyStr] = os.getenv('TEST_MODE', None)
_database_to_use: Optional[AnyStr] = os.getenv('TEST_DATABASE', None)
_conn = None


@asynccontextmanager
async def lifespan(service: FastAPI) -> None:

    print("APPSTART")
    print("-" * 100)
    for route in service.routes:
        print(route.path)

    await startup_event()
    yield
    await shutdown_event()


def get_service() -> FastAPI:
    if hasattr(get_service, 'service'):
        return get_service.service

    from base4 import configuration

    cfg = configuration('services')

    docs_path = pydash.get(cfg, 'general.docs_uri', '/api/docs')
    openapi_path = pydash.get(cfg, 'general.openapi_uri', '/api/openapi')
    redoc_path = pydash.get(cfg, 'general.redoc_uri', '/api/redoc')

    service: FastAPI = FastAPI(lifespan=lifespan, openapi_url=openapi_path, docs_url=docs_path, redoc_url=redoc_path)

    get_service.service: FastAPI = service

    return service


async def startup_event(services: List[str] = None) -> None:
    """
    Code which is executed before starting application.
    If application is in test mode it'll execute specific
    startup method for test mode.

    :return: None
    """

    # TODO: ako nemas boljinacin da proguras ovo, ucitaj ih iz services.yaml fajla ako nisu dosli
    if not services:
        services = []
        with open(current_file_path + '/services.yaml') as f:
            services = yaml.safe_load(f)['services']
            services = [list(s.keys())[0] for s in services]

        # services = ['tickets', 'bp']

    if isinstance(_test, str):
        return await test_startup_event(services)

    # service mode vvvv

    for svc_name in services:
        DATABASE: DatabaseConfig = DatabaseConfig(
            svc_name=svc_name,
        )

        await _initialize_tortoise_models(conf=DATABASE, conn='conn_' + svc_name)


async def shutdown_event() -> None:
    if isinstance(_test, str):
        return await test_shutdown_event()


""" TEST MODE """


async def test_startup_event(services: List[str]) -> None:
    """
    Test startup events such as initializing db, models...

    :return: None
    """

    if _database_to_use == 'sqlite':
        await _initialize_tortoise_models(test_mode=True, conn='conn_test')
        return

    DATABASE: DatabaseConfig = DatabaseConfig(_testmode=True, db_name=os.getenv('DB_TEST', None), svc_name='test')

    await _delete_and_create_test_database(conf=DATABASE)

    await _initialize_tortoise_models(conf=DATABASE, conn='conn_test', test_mode=True, services=services)
    ...


async def test_shutdown_event() -> None:
    await Tortoise.close_connections()


async def _delete_and_create_test_database(conf: DatabaseConfig) -> None:
    """
    Droping test database if exists and creating new.

    :param conf: Database configuration.
    :return:
    """

    _connection: Dict = {'user': conf.db_postgres_user, 'password': conf.db_postgres_password, 'host': conf.db_postgres_host, 'port': int(conf.db_postgres_port), 'database': 'template1'}

    try:
        _conn: asyncpg.connection.Connection = await asyncpg.connect(**_connection)
    except Exception:
        raise

    try:
        exists: int = await _conn.fetchval('SELECT 1 FROM pg_database WHERE datname = $1', 'template1')

        if exists:

            while True:

                kill_attempt = 0
                try:
                    await _conn.execute(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = $1
                        """,
                        conf.db_name,
                    )

                    break
                except Exception:
                    kill_attempt += 1
                    if kill_attempt > 3:
                        raise NameError('Could not kill connections')
                    await asyncio.sleep(kill_attempt)

            await _conn.execute(f'DROP DATABASE {conf.db_name}')

        await _conn.execute(f'CREATE DATABASE {conf.db_name}')

    except Exception as e:
        raise

    finally:
        await _conn.close()


async def _initialize_tortoise_models(conf: Optional[DatabaseConfig] = None, conn: str = 'default', test_mode: bool = False, services=None) -> None:
    """
    Initialize Tortoise ORM with the provided configuration.

    Args:
        conf (Dict): Configuration dictionary containing database connection details.
    """

    _url: AnyStr = f'sqlite://:memory:'
    if conf:
        _url: AnyStr = f'postgres://{conf.db_postgres_user}:{conf.db_postgres_password}@{conf.db_postgres_host}:{conf.db_postgres_port}/{conf.db_name}'
    
    
    TORTOISE_ORM['connections'][conn] = _url

    if services:
        apps = {}
        for app in TORTOISE_ORM['apps']:
            if app in services:  # or app=='aerich':
                apps[app] = TORTOISE_ORM['apps'][app]

        TORTOISE_ORM['apps'] = apps

    if test_mode:
        for conn in TORTOISE_ORM['connections']:
            TORTOISE_ORM['connections'][conn] = TORTOISE_ORM['connections']['conn_test']
        ...

    try:
        await Tortoise.init(config=TORTOISE_ORM)

        await Tortoise.generate_schemas()
    except Exception:
        raise

    return


service: FastAPI = get_service()
