# base4/utils/file_utils.py

import os
import sys
from pathlib import Path

import pkg_resources


def is_installed_package():
    """
    Determines if the code is running from an installed package.

    :return: True if running from an installed package, False if running from source.
    """
    try:
        dist = pkg_resources.get_distribution('base4')
        return True
    except pkg_resources.DistributionNotFound:
        return False


def get_project_root():
    """
    Returns the absolute path to the root directory of the base4 project.
    This works whether the code is run from the source directory,
    or from an installed package.
    """
    if is_installed_package():
        # we are running in a bundle

        if os.getenv('APPLICATION_RUN_MODE', 'local') in ('docker','docker-monolith'):
            # we are running in docker
            return '/app/'

        #TODO Remove - but change this env in v4 project and then remuve this

        if os.getenv('V4INSTALLATION', 'local') in ('docker','docker-monolith'):
            # we are running in docker
            return '/app/'

        # local .venv installation
        return Path(sys.executable).parent.parent.parent
    else:
        # we are running in a normal Python environment
        return Path(__file__).parent.parent.parent.parent.parent

def get_project_config_folder():

    #TODO: remove src when structure is changed

    return get_project_root() / 'src' / 'config'

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

#
# # Example usage
# if __name__ == "__main__":
#     print(f"Project root: {get_project_root()}")
#     print(f"Path to a file: {get_file_path('security/private_key.pem')}")
#     # Uncomment to test file reading (adjust the path as needed)
#     # print(f"Content of README.md: {read_file('README.md')}")
