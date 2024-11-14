import os

import dotenv
import socketio

dotenv.load_dotenv()

SIO_REDIS_HOST = os.getenv('SOCKETIO_REDIS_HOST')
SIO_REDIS_PORT = os.getenv('SOCKETIO_REDIS_PORT')
HOST = os.getenv('SOCKETIO_HOST')


def sio_client_manager(write_only=False):
    return socketio.AsyncRedisManager(f'redis://%s:%s/0' % (SIO_REDIS_HOST, SIO_REDIS_PORT), write_only=write_only)


def extract_domain(host):
    try:
        host = host.split('://')[1]
    except:
        pass
    finally:
        return '.'.join(host.split('.')[-2:])


sio_connection = sio_client_manager(write_only=False)


async def emit(event, data=None, room=None, connection=None):
    ns = extract_domain(HOST) + '='
    if connection:
        return await connection.emit(event=event, data=data, room=ns + room if room else None)
    return await sio_connection.emit(event=event, data=data, room=ns + room if room else None)
