import os

from base4.utilities.files import get_project_root


def do():
    try:
        print('get_project_root()', get_project_root())
        os.system(f'pip install -r {get_project_root()}/scripts/pip/requirements-old.txt')
    except:
        print('[*] backup requirements not found')


if __name__ == '__main__':
    do()
