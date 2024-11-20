import os

from base4.utilities.files import get_project_root


def do():
    project_root = str(get_project_root())

    os.system(
        f'''
    cd {project_root}
    TEST_DATABASE=sqlite pytest -n 8 --disable-warnings tests --no-cov
    cd -
    '''
    )


if __name__ == '__main__':
    do()
