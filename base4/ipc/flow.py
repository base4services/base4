import datetime
import uuid
from typing import AnyStr, Dict, List, Optional

from base4.ipc.ipc import ipc


async def create_flow_message(handler, body: dict) -> Dict:
    return await ipc(handler, 'flow', 'POST', '', body=body)

from base4.utilities.cache import memoize

async def get_timesheet_for_flow_item_start(handler, item, attribute):

    async def get_timesheet_object_for_flow_item(handler, item) -> Dict:

        @memoize(ttl=1)
        async def get_info(item):
            return await ipc(handler, 'timesheet', 'GET', f'/by-flow-item/{item.id}')

        return await get_info(item)

    #TODO: kesiraj A na 1 sec u redis-u

    a = await get_timesheet_object_for_flow_item(handler, item)

    if attribute == 'start_datetime':
        if 'date' in a and 'start' in a and a['date'] and a['start']:
            return datetime.datetime.strptime(a['date']+' '+a['start'], '%Y-%m-%d %H:%M:%S')
    if attribute == 'end_datetime':
        if 'date' in a and 'end' in a and a['date'] and a['end']:
            return datetime.datetime.strptime(a['date']+' '+a['end'], '%Y-%m-%d %H:%M:%S')
    if attribute == 'duration':
        if 'hhmm' in a:
            return a['hhmm']

    return None