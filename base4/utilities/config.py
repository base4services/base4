import os
import re

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


def yaml_to_env(yaml_cfg):
    env_path = f'{current_file_path}/.env'
    if not os.path.exists(env_path):
        with open(env_path, 'a') as file:
            with open(env_path, 'w') as file:
                file.write('')
    
    os.chmod(env_path, 0o666)
    flat_config = yaml_to_obj(load_yaml_config(yaml_cfg))
    with open(env_path, 'w+') as env_file:
        env_file.write('''# THIS IS AN AUTO-GENERATED AND PROTECTED FILE. PLEASE USE
# THE 'gen --env' SCRIPT TO GENERATE THIS FILE. DO NOT EDIT DIRECTLY
# AS IT CAN BE OVERWRITTEN.\n''')
        for key, value in flat_config.items():
            if key == 'db_postgres_databases':
                continue
            env_file.write(f"{key.upper()}={value}\n")
        env_file.write(f"## PROJECT DATABASES:\n")
        env_file.write("DB_TEST=test_${DB_PREFIX}\n")
        for p in flat_config['db_postgres_databases'].split(','):
            env_file.write("DB_%s=${DB_PREFIX}\n" % (p.upper(), ))
        
        env_file.write(f"DATABASES=({' '.join(["$DB_"+i.upper() for i in flat_config['db_postgres_databases'].split(',')])})" )
        
    os.chmod(env_path, 0o444)
