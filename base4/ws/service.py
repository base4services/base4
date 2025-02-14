import os

import socketio
import ujson as json
from fastapi import FastAPI

from base4.utilities.db.async_redis import get_redis

from base4.utilities import base_dotenv
from base4.utilities.security.jwt import decode_token

base_dotenv.load_dotenv()

import inspect

from base4.utilities.logging.setup import get_logger
from base4.utilities.ws import extract_domain, sio_client_manager

SIO_ALLOWED_ORIGINS = os.getenv('SOCKETIO_ALLOWED_ORIGINS').split(',')
SIO_ADMIN_PORT = os.getenv('SOCKETIO_ADMIN_PORT')
SIO_REDIS_PORT = int(os.getenv('SOCKETIO_REDIS_PORT', '6379'))
print(SIO_ALLOWED_ORIGINS)
# SIO_ALLOWED_ORIGINS = os.getenv('SOCKETIO_ALLOWED_ORIGINS').split(',')
# SIO_ADMIN_PORT = '8002'
# SIO_REDIS_PORT = 6379

logger = get_logger()

MAIN_CHANNELS = ['hotels']


class BaseSocketServer(object):
    def __init__(self):
        self.sio = socketio.AsyncServer(
            json=json,
            async_handlers=True,
            cors_allowed_origins=['https://admin.socket.io', 'http://127.0.0.1:8001', 'admin.socket.io', 'https://admin.socket.io'],
            async_mode='asgi',
            logger=True,
            always_connect=False,
            engineio_logger=True,
            ping_interval=20,
            ping_timeout=5,
            client_manager=sio_client_manager(write_only=False),
        )
        self.app = FastAPI()
        self.sio_app = socketio.ASGIApp(self.sio, other_asgi_app=self.app)
        self.rdb = get_redis()
        self.setup_admin()
        self.register_events()

    def setup_admin(self):
        """Configures admin access settings."""
        self.sio.instrument(
            auth={'username': 'admin', 'password': 'd1g1t4lcub3'},
            mode='development',
            read_only=False,
            server_id=f'port:{SIO_ADMIN_PORT}',
            namespace=f'/admin',
            server_stats_interval=1,
        )

    def get_namespace(self, sid):
        """Gets the namespace based on client environment."""
        try:
            return extract_domain(self.sio.get_environ(sid)['asgi.scope']['headers'][4][1].decode('utf8')) + '='
        except Exception:
            return '*='

    def register_events(self):
        """Automatically registers Socket.IO events based on method names."""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("on_"):  # Check if the method name starts with 'on_'
                event_name = name[3:]  # Remove 'on_' prefix to get the event name
                self.sio.on(event_name, method)  # Register the method as an event handler

    async def on_connect(self, sid, environ=None, auth=None):
        query_params = environ.get("QUERY_STRING", "")
        jwt_token = None
        for param in query_params.split("&"):
            if param.startswith("jwt_token="):
                jwt_token = param.split("=")[1]

        decoded_jwt_data = decode_token(jwt_token)
        if not decoded_jwt_data:
            await self.sio.disconnect(sid)
            return ConnectionRefusedError('AUTHENTICATION_FAILED')

        rdb_session = await self.rdb.get(f"session:{decoded_jwt_data.session_id}")
        if not rdb_session:
            await self.sio.disconnect(sid)
            return ConnectionRefusedError('AUTHENTICATION_FAILED')
        if not isinstance(rdb_session, dict):
            rdb_session = json.loads(rdb_session)

        try:
            await self.sio.save_session(sid, rdb_session)
        except:
            await self.sio.disconnect(sid)
            return ConnectionRefusedError('AUTHENTICATION_FAILED')

        for sub in MAIN_CHANNELS:
            await self.sio.enter_room(sid=sid, room=sub)

        await self.sio.emit('message', {'data': f'successfully connected to the server'}, to=sid)

    async def on_disconnect(self, sid):
        print('on_disconnect', sid)
        for room in self.sio.rooms(sid):
            logger.info('%s%s', sid, room)
            await self.sio.leave_room(sid=sid, room=room)

    async def on_connect_error(self, data):
        print("on_connect_error", data)
        logger.info('%s%s', data)
