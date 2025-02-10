import os
import logging
from base4.utilities.files import env

def check_environment(print_check: bool=True):

    log = logging.getLogger()

    from base4.utilities.app_run_modes import app_run_modes

    app_run_mode = os.getenv('APPLICATION_RUN_MODE', None)

    if app_run_mode not in app_run_modes:
        log.critical('APPLICATION_RUN_MODE environment variable not set, expecting one of: '+','.join(app_run_modes))
        return False

    if print_check:
        print('APPLICATION_RUN_MODE:', os.getenv('APPLICATION_RUN_MODE'))

    try:
        env_file = env()
        with open(env_file,'rt'):
            ...

        if print_check:
            print('.env file:', env_file)

    except Exception:
        log.critical(f'Error reading environment file: {env_file}')
        return False

    return True