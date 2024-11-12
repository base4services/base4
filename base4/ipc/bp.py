import uuid
from typing import AnyStr, Dict, List, Optional

from base4.ipc.ipc import ipc
from base4.utilities.cache import memoize


@memoize(ttl=300)
async def get_bp_site(handler, site_id: uuid.UUID, fields: List[AnyStr], return_value_for_key: AnyStr = None) -> Dict:
    return await ipc(handler, 'bp', 'GET', f'/sites/{site_id}', params={'fields': fields}, return_value_for_key=return_value_for_key)


@memoize(ttl=300)
async def get_bp(handler, bp_id: uuid.UUID, fields: List[AnyStr], return_value_for_key: AnyStr = None) -> Dict:
    return await ipc(handler, 'bp', 'GET', f'/bp/{bp_id}', params={'fields': fields}, return_value_for_key=return_value_for_key)


@memoize(ttl=300)
async def get_bp_by_external_id(handler, external_id: AnyStr) -> Dict:
    return await ipc(handler, 'bp', 'GET', f'/bp/by-external/{external_id}')


async def create_new_contacts_on_bp(handler, bp_id: uuid.UUID, contacts: List[Dict]) -> Dict:
    res = await ipc(handler, 'bp', 'POST', f'/{bp_id}/contacts/multiple', body={'contacts': contacts})

    return res


async def get_bp_id2dict_contacts_by_bp_and_provided_ids(
    handler,
    bp_id: uuid.UUID,
    contact_ids: Optional[None | List[uuid.UUID]] = None,
) -> Dict:
    if contact_ids:
        filters = 'and(bp_id="' + str(bp_id) + '",id__in=[' + ','.join([f'"{x}"' for x in contact_ids]) + '])'
    else:
        filters = f'bp_id="{bp_id}"'

    return await ipc(
        handler,
        'bp',
        'GET',
        f'/contacts',
        params={
            'response_format': 'key-value',
            'key_value_response_format_key': 'id',
            'filters': filters,
        },
    )
