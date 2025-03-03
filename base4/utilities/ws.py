import json
import os

import socketio

from base4.utilities import base_dotenv
base_dotenv.load_dotenv()


SIO_REDIS_HOST = os.getenv('SOCKETIO_REDIS_HOST')
SIO_REDIS_PORT = os.getenv('SOCKETIO_REDIS_PORT')


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
    if os.getenv('TEST_MODE'):
        return

    if data:
        data = json.loads(json.dumps(data,ensure_ascii=False, default=str))

    # TODO: Napraviti TEST WS, ako ne nadjemo neki bolji nacin da testiram WS, moze ovaj emit da upisuje u neki redis queue i da ga iz testa samo tamo citamo

    print("\n"*2)
    print("PUBL TO WS ", event, data, room)
    print("\n"*2)

    if connection:
        return await connection.emit(event=event, data=data, room=room if room else None)
    return await sio_connection.emit(event=event, data=data, room=room if room else None)
