#
import uuid
from typing import AnyStr, Dict, List

from black.linegen import partial

from base4.utilities.cache import memoize

from .ipc import ipc
from .tickets import get_single_ticket

try:
    # TODO: ovo mora da se skine iz base, posto base ne treba da zna za druge projte
    from shared.utils.v3_api_utils import make_v3_api_request
except Exception as e:
    pass

import pydash

from base4.utilities.http.methods import HttpMethod

deal_field_map = {
    "title": "deal.short_description",
    "id_status": None,
    "status": None,
    "id_priority": None,
    "priority": None,
    "status_id": "deal.status_id",
    "stage_id": "deal.stage_id",

}
tickets_field_map = {
    "title": "title",
    "id_status": "id_status",
    "status": "status",
    "id_priority": "id_priority",
    "priority": "priority",
    "status_id": None,
    "stage_id": None,

}


async def get_workflow_item_attribute(handler, item_type_id, item_id: uuid.UUID, field: str) -> Dict | None:
    if str(item_type_id) == Lookups.Workflows.WorkflowItemTypes.TICKETS:
        ticket_data = await get_single_ticket(handler, item_id)
        return pydash.get(ticket_data, tickets_field_map[field])
    elif str(item_type_id) == Lookups.Workflows.WorkflowItemTypes.SALES:
        deal_data = await make_v3_api_request(handler=handler, service="deals", url=f"{item_id}", method=HttpMethod.GET)
        if not deal_field_map.get(field):
            return None
        return pydash.get(deal_data, deal_field_map[field])
    else:
        raise Exception('Unknown item type')
