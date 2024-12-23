# base4/utils/file_utils.py

import importlib.metadata
import os
import sys
from pathlib import Path


def is_installed_package():
    """
    Determines if the code is running from an installed package.

    :return: True if running from an installed package, False if running from source.
    """
    try:
        # Replace 'base4' with the actual package name you are checking
        dist = importlib.metadata.distribution('base4')
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def get_project_root():
    """
    Returns the absolute path to the root directory of the base4 project.
    This works whether the code is run from the source directory,
    or from an installed package.
    """
    if is_installed_package():
        # we are running in a bundle

        if os.getenv('APPLICATION_RUN_MODE', 'local') in ('docker', 'docker-monolith'):
            # we are running in docker
            return Path('/app/')

        # TODO Remove - but change this env in v4 project and then remuve this

        if os.getenv('V4INSTALLATION', 'local') in ('docker', 'docker-monolith'):
            # we are running in docker
            return Path('/app/')
        return Path(sys.executable).parent.parent.parent
    return Path(__file__).parent.parent.parent.parent.parent


def get_project_config_folder():
    return get_project_root() / 'config'


def get_file_path(relative_path):
    """
    Returns the absolute path for a file given its path relative to the project root.

    :param relative_path: Path relative to the project root
    :return: Absolute path to the file
    """
    return str(get_project_root()) + '/' + relative_path.lstrip('/')


def read_file(relative_path):
    """
    Reads and returns the content of a file given its path relative to the project root.

    :param relative_path: Path relative to the project root
    :return: Content of the file
    """
    with open(get_file_path(relative_path), 'r') as f:
        return f.read()


def root():
    return get_project_root()

def config():
    return get_project_config_folder()

def src():
    return root() / 'src'

def shared():
    return src() / 'shared'

def tests():
    return root() / 'tests'

def logs():
    return '/var/log/sophie-docs'

def env():
    return root() / '.env'

def tmp(filename=None):
    if not filename:
        return Path('/tmp')

    return Path('/tmp') / filename

def assets(service=None, asset=None):

    if not service and not asset:
        return src() / 'assets'

    if not service:
        return src() / 'assets' / asset

    if not asset:
        return src() / 'services' / service / 'assets'

    return src() / 'services' / service / 'assets' / asset
