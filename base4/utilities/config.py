import datetime
import os
import re
import sys

import yaml

from base4.utilities.files import get_project_root

current_file_path = str(get_project_root())


def replace_env_vars(value):
    if isinstance(value, str):
        pattern = r'\${([^}^{]+)}'
        matches = re.finditer(pattern, value)
        for match in matches:
            env_var = match.group(1)
            env_value = os.getenv(env_var, '')
            value = value.replace(f'${{{env_var}}}', env_value)
        return value
    elif isinstance(value, dict):
        return {k: replace_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [replace_env_vars(v) for v in value]
    return value


def load_yaml_config(fname):
    with open(f'{current_file_path}/config/{fname}.yaml') as f:
        config = yaml.safe_load(f)
        config = replace_env_vars(config)
        return config


def yaml_to_obj(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(yaml_to_obj(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, ','.join(map(str, v))))
        else:
            items.append((new_key, v))
    return dict(items)


def yaml_to_env(yaml_cfg, app_run_mode: str = None):

    app_environment = os.getenv('RUNNING_APP_ENVIRONMENT', None)

    env_keys = set()

    if not app_environment:
        sys.exit('APPLICATION_ENVIRONMENT environment variable not set')


    from base4.utilities.app_run_modes import app_run_modes, app_environments

    if app_run_mode in (None, 'default'):
        app_run_mode = os.getenv('APPLICATION_RUN_MODE', None)

    if not app_run_mode or app_run_mode not in app_run_modes:
        sys.exit('APPLICATION_RUN_MODE environment variable not set, expecting one of: docker, docker-monolith, micro-services, monolith')

    env_path = f'{current_file_path}/.env.{app_run_mode}'
    if not os.path.exists(env_path):
        with open(env_path, 'a') as file:
            with open(env_path, 'w') as file:
                file.write('')

    os.chmod(env_path, 0o666)
    flat_config = yaml_to_obj(load_yaml_config(yaml_cfg))
    with open(env_path, 'w+') as env_file:
        env_file.write(
            f'''# THIS IS AN AUTO-GENERATED AND PROTECTED FILE. PLEASE USE
# THE bmanager compile-env SCRIPT TO GENERATE THIS FILE. DO NOT EDIT DIRECTLY
# AS IT CAN BE OVERWRITTEN.
#
# FILE GENERATED ON: {datetime.datetime.now()}

\n'''
        )
        for key, value in flat_config.items():
            if key == 'db_postgres_databases':
                continue

            # if 'dev-igor' in key:
            #     breakpoint()

            if f'[{app_run_mode}|{app_environment}]' in key:
                key = key.replace(f'[{app_run_mode}|{app_environment}]', '')

            elif f'[{app_run_mode}]' in key:
                key = key.replace(f'[{app_run_mode}]', '')


            else:
                cont=False

                for opt in app_run_modes:

                    for opt2 in app_environments:
                        if f'[{opt}|{opt2}]' in key:
                            cont = True
                            # breakpoint()
                            break

                    if f'[{opt}]' in key:
                        cont = True
                        break
                if cont:
                    continue

            if '[' in key or ']' in key:
                sys.exit(f'Invalid key: {key}. Keys should not contain "[" or "]"')

            if key.upper() in env_keys:
                continue

            env_keys.add(key.upper())

            env_file.write(f"{key.upper()}={value}\n")
        env_file.write("DB_TEST=test_${DB_PREFIX}\n")
        for p in flat_config['db_postgres_databases'].split(','):
            print(os.getenv('DB_USE_SEPARATED_DATABASES', None), type(os.getenv('DB_USE_SEPARATED_DATABASES', None)))
            if os.getenv('DB_USE_SEPARATED_DATABASES', None) in ('true', 'True',True, 1):
                env_file.write("DB_%s=${DB_PREFIX}_%s\n" % (p.upper(),p.upper()))
            else:
                env_file.write("DB_%s=${DB_PREFIX}\n" % (p.upper(),))

        env_file.write(f"DATABASES=({' '.join(["$DB_"+i.upper() for i in flat_config['db_postgres_databases'].split(',')])})")

    os.chmod(env_path, 0o444)
    return env_path
