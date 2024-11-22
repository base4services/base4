import uuid
from typing import AnyStr, Dict, List, Optional
import datetime

from base4.ipc.ipc import ipc


async def create_flow_message(handler, body: dict) -> Dict:
    return await ipc(handler, 'flow', 'POST', '', body=body)

async def get_timesheet_for_flow_item_start(handler, item, attribute):
    if attribute == 'start_datetime':
        return datetime.datetime(2024,1,1,10,0,0)
        # return '2024-01-01 10:00:00'
    if attribute == 'end_datetime':
        return datetime.datetime(2024,1,1,12,0,0)
        # return '2024-01-01 14:00:00'
    if attribute == 'duration':
        return '02:00'

    return "N/A"