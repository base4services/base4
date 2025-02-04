import os

import dotenv
import socketio
import ujson
from fastapi import FastAPI

from base4.utilities.db.async_redis import get_redis

dotenv.load_dotenv()
import inspect

from base4.utilities.logging.setup import get_logger
from base4.utilities.ws import extract_domain, sio_client_manager

SIO_ALLOWED_ORIGINS = os.getenv('SIO_ALLOWED_ORIGINS').split(',')
SIO_ADMIN_PORT = os.getenv('SIO_ADMIN_PORT')
SIO_REDIS_PORT = int(os.getenv('SIO_REDIS_PORT', '6379'))

logger = get_logger()


class BaseSocketServer(object):
    def __init__(self):
        self.sio = socketio.AsyncServer(
            json=ujson,
            async_handlers=True,
            cors_allowed_origins=['https://admin.socket.io', 'http://127.0.0.1:8000', 'admin.socket.io', 'https://admin.socket.io', ''],
            async_mode='asgi',
            logger=False,
            always_connect=False,
            engineio_logger=False,
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

    async def do_auth(self, sid, token):
        """Performs authentication with the token."""
        if token:
            try:
                token = token.decode('utf-8')
            except AttributeError:
                pass
            # Additional auth logic here
            return True
        return False

    def get_namespace(self, sid):
        """Gets the namespace based on client environment."""
        try:
            return extract_domain(self.sio.get_environ(sid)['asgi.scope']['headers'][4][1].decode('utf8')) + '='
        except Exception:
            return '*='

    def register_events(self):
        """Automatically registers Socket.IO events based on method names."""
        # Loop through all methods of this instance
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("on_"):  # Check if the method name starts with 'on_'
                event_name = name[3:]  # Remove 'on_' prefix to get the event name
                self.sio.on(event_name, method)  # Register the method as an event handler

    async def on_connect(self, sid, environ=None, auth=None):
        print('on_connect', sid)

    async def on_authenticate(self, sid, token):
        print('on_authenticate', sid)
        logger.info(sid)
        if token:
            return await self.do_auth(sid, token)
        return ConnectionRefusedError('AUTHENTICATION_FAILED')

    async def on_disconnect(self, sid):
        print('on_disconnect', sid)
        for room in self.sio.rooms(sid):
            logger.info('%s%s', sid, room)
            await self.sio.leave_room(sid=sid, room=room)

    async def on_connect_error(self, data):
        print("on_connect_error", data)
        logger.info('%s%s', data)
