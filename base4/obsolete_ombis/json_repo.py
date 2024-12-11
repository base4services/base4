import os
from typing import Literal

import ujson as json

from .fetch import *

current_file_folder = os.path.dirname(os.path.realpath(__file__))

from base4.utilities.files import get_file_path

OMBIS_REPO_FOLDER = get_file_path('ombis_repo/')  # current_file_folder + '/../../../ombis_repo/'

...


async def get_geoloc():
    if hasattr(get_geoloc, 'result'):
        return get_geoloc.result

    async def get_items(input_file):

        if not os.path.exists(OMBIS_REPO_FOLDER + input_file):
            if input_file.startswith('countries'):
                await fetch_countries(result_file=OMBIS_REPO_FOLDER + input_file)
            if input_file.startswith('regions'):
                await fetch_regions(result_file=OMBIS_REPO_FOLDER + input_file)
            if input_file.startswith('provinces'):
                await fetch_provinces(result_file=OMBIS_REPO_FOLDER + input_file)
            if input_file.startswith('municipalities'):
                await fetch_municipalities(result_file=OMBIS_REPO_FOLDER + input_file)

        with open(OMBIS_REPO_FOLDER + input_file, 'rt') as f:
            items = json.load(f)

        res = {}
        for item in items:
            res[int(item)] = items[item]['Fields']['Name']

        return res

    countries = await get_items('countries.json')
    regions = await get_items('regions.json')
    provinces = await get_items('provinces.json')
    municipalities = await get_items('municipalities.json')

    get_geoloc.result = {'countries': countries, 'regions': regions, 'provinces': provinces, 'municipalities': municipalities}
    return get_geoloc.result


async def geoloc(geo_type: Literal['country', 'region', 'province', 'municipality'], _id: int):
    if not _id:
        return None

    if isinstance(_id, str):
        _id = int(_id.split('/')[-1])

    try:
        repo = await get_geoloc()

        if geo_type == 'country':
            return repo['countries'][_id]
        elif geo_type == 'region':
            return repo['regions'][_id]
        elif geo_type == 'province':
            return repo['provinces'][_id]
        elif geo_type == 'municipality':
            return repo['municipalities'][_id]
        else:
            raise ValueError('Invalid geo_type')
    except Exception as e:
        raise


async def departments():
    if not os.path.exists(OMBIS_REPO_FOLDER + 'departments.json'):
        await fetch_departments(result_file=OMBIS_REPO_FOLDER + 'departments.json')

    with open(OMBIS_REPO_FOLDER + 'departments.json', 'rt') as f:
        items = json.load(f)

    res = {}
    for item in items:
        res[int(item)] = items[item]['Fields']['Name']

    return res


#
# async def get_employee(_id):
#     if not _id:
#         return None
#     if isinstance(_id, str):
#         _id = int(_id.split('/')[-1])
#
#     input_file = 'employees.json'
#
#     if not os.path.exists(OMBIS_REPO_FOLDER + input_file):
#         await fetch_employees()
#
#     with open(OMBIS_REPO_FOLDER + input_file, 'rt') as f:
#         items = json.load(f)
#
#

# if __name__ == '__main__':
# print(geoloc('country', 2446))
