import os

import ujson as json

current_file_dir = os.path.dirname(os.path.realpath(__file__))

from base4.utilities.files import get_file_path


def loguser2user_ombisid(loguser_id: int) -> int:
    if not hasattr(loguser2user_ombisid, 'data'):
        with open(get_file_path('ombis_repo/logusers.json'), 'rt') as f:
            data = json.load(f)
            loguser2user_ombisid.data = {int(u): data[u]['Fields']['InternalNumber'] for u in data}

    res = loguser2user_ombisid.data[loguser_id]
    if res == -2:
        res = 137

    return res


def employe2user(employe_id: int) -> int:
    if not hasattr(employe2user, 'data'):
        with open(current_file_dir + '/../../../ombis_repo/employees.json', 'rt') as f:
            data = json.load(f)
            employe2user.data = {int(u): data[u]['Fields'].get('UserID') for u in data}

    res = employe2user.data[employe_id]
    return res


if __name__ == '__main__':
    # print(loguser2user_ombisid(228))

    print(employe2user(107))
