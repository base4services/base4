import uuid
from typing import AnyStr, Dict, List

from base4.utilities.cache import memoize

from .ipc import ipc


@memoize(ttl=3600)
async def get_department_field(handler, id_department: uuid.UUID, field: str) -> Dict:
    return await ipc(handler, 'tenants', 'GET', f'/departments/{id_department}/{field}', return_value_for_key='value')


@memoize(ttl=3600)
async def get_user(handler, id_user: uuid.UUID):
    return await ipc(handler, 'tenants', 'GET', f'/users/{id_user}')


async def get_user_attr(handler, id_user: uuid.UUID, attr: str):
    # breakpoint()
    user = await get_user(handler, id_user)
    return user[attr]


async def login(handler, username, password):
    res = await ipc(
        handler,
        'tenants',
        'POST',
        '/users/login',
        body={'username': username, 'password': password},
    )

    return res


@memoize(ttl=3600)
async def get_department_by_external_id(handler, external_id: int):
    return await ipc(handler, 'tenants', 'GET', f'/departments/by-external-id/{external_id}')


@memoize(ttl=3600)
async def get_user_by_external_id(handler, external_id: int):
    return await ipc(handler, 'tenants', 'GET', f'/users/by-external-id/{external_id}')


@memoize(ttl=3600)
async def get_user_by_external_employee_id(handler, external_id: int):
    return await ipc(handler, 'tenants', 'GET', f'/users/by-external-employee-id/{external_id}')


async def get_mapped_by_external_employee_id(handler):
    return await ipc(handler, 'tenants', 'GET', f'/users/by-external-employee-id')


@memoize(ttl=3600)
async def get_user_field(handler, id_user: uuid.UUID, field: str) -> str:
    try:
        return await ipc(handler, 'tenants', 'GET', f'/users/{id_user}/{field}')
    except Exception as e:
        raise


async def users_by_id(handler, ids_user: List[uuid.UUID]):
    params = {'filter': 'id_user__in=({})'.format(','.join([str(id_user) for id_user in ids_user]))}
    return await ipc(handler, 'tenants', 'GET', f'/users', params=params)


async def get_ombis_users_table(handler):
    return await ipc(handler, 'tenants', 'GET', '/users', params={'profile': 'users_ombis_table', 'per_page': 999999})


async def get_org_units_and_users(handler):
    return await ipc(handler, 'tenants', 'GET', '/users/org_units_and_users', params={'profile': 'org_units_and_users', 'per_page': 999999})


async def get_org_units(handler):
    try:
        res = await ipc(handler, 'tenants', 'GET', '/org_units', params={'profile': 'org_units', 'per_page': 999999, 'only_data': True})
    except Exception as e:
        raise

    return res
