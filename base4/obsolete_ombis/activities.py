import os

import ujson as json

current_file_dir = os.path.dirname(os.path.realpath(__file__))
from base4.utilities.files import get_file_path


def activitiy_by_id(id: int, field='Name') -> int:

    if not hasattr(activitiy_by_id, 'data'):
        with open(get_file_path('ombis_repo/activities.json'), 'rt') as f:
            data = json.load(f)
            activitiy_by_id.data = {int(u): data[u]['Fields'] for u in data}

    res = activitiy_by_id.data[id]

    return res[field]


if __name__ == '__main__':

    print(activitiy_by_id(6))
