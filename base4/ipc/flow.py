import uuid
from typing import AnyStr, Dict, List, Optional

from base4.ipc.ipc import ipc


async def create_flow_message(handler, body: dict) -> Dict:
    return await ipc(handler, 'flow', 'POST', '', body=body)
