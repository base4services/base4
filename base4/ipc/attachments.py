import uuid
from typing import AnyStr, Dict, List, Optional

from base4.ipc.ipc import ipc


async def create_attachments(handler, body: dict) -> Dict:
    return await ipc(handler, 'attachments', 'POST', '/files', body=body)
