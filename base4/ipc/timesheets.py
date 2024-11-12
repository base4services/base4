from typing import AnyStr, Dict, List, Optional

from base4.ipc.ipc import ipc


async def create_timesheet(handler, body: dict) -> Dict:
    return await ipc(handler, 'timesheet', 'POST', '', body=body)
