import uuid
from typing import AnyStr, Dict, List

from base4.utilities.cache import memoize

from .ipc import ipc

# TODO: ADD TIME CACHING MEMOIZE


@memoize(ttl=2)
async def get_ticket_info_for_timesheet(handler, id_ticket):
    ...

    try:
        res = await ipc(
            handler,
            'tickets',
            'GET',
            f'/{id_ticket}/cache/timesheet',
        )
    except Exception as e:
        raise

    return res


async def get_ticket_ids_by_ombis_ids(handler, ombis_ids: List[int]) -> Dict:
    ...

    try:
        res = await ipc(
            handler,
            'tickets',
            'GET',
            f'/ombis/by_ids/{",".join(map(str, ombis_ids))}',
        )
    except Exception as e:
        raise

    return res


@memoize(ttl=60)
async def get_single_ticket(handler, id_ticket):
    try:
        res = await ipc(
            handler,
            'tickets',
            'GET',
            f'/{id_ticket}',
        )
    except Exception as e:
        raise

    return res


async def create_ticket(handler, body: dict):
    try:
        res = await ipc(
            handler,
            'tickets',
            'POST',
            f'',
            body=body
        )
    except Exception as e:
        raise

    return res
