#!/usr/bin/env python3

import os
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
import click
import dotenv
import git
import yaml

import base4.scripts.gen_model as gen_model
import base4.scripts.gen_schemas as gen_schemas
import base4.scripts.gen_tables as gen_tables
from base4 import configuration
from base4.scripts.gen_tables import gen_profile
from base4.scripts.pip.down import do as p_down
from base4.scripts.pip.up import do as p_up
from base4.scripts.yaml_compiler import compile_main_config, update_config_ac
from base4.utilities.config import yaml_to_env
from base4.utilities.files import get_project_root

dotenv.load_dotenv()

project_root = str(get_project_root())

#TODO: ovo pokupiti listanjem git repo-a
existing_service_templates = ['base4tenants', 'base4ws', 'base4sendmail', 'base4service_template']

def gen4svc(svc_name, location, gen=None):
    if not gen:
        gen = {'models', 'schemas', 'tables'}

    if 'models' in gen:
        gen_model.save(
            project_root + f'/{location}/yaml_sources/{svc_name}_model.yaml',
            project_root + f'/{location}/models/generated_{svc_name}_model.py',
        )
    if 'schemas' in gen:
        gen_schemas.save(
            project_root + f'/{location}/yaml_sources/{svc_name}_schema.yaml',
            project_root + f'/{location}/schemas/generated_{svc_name}_schema.py',
        )
    if 'tables' in gen:
        gen_tables.save(
            svc_name,
            project_root + f'/{location}/yaml_sources/{svc_name}_table.yaml',
            project_root + f'/{location}/yaml_sources/{svc_name}_model.yaml',
            project_root + f'/{location}/schemas/generated_{svc_name}_table.py',
        )


    # todo, sredi ovo
    # if 'tables' in gen:
    #     gen_tables.save(
    #         svc_name,
    #         project_root + f'/{location}/yaml_sources/{object_name}_table.yaml',
    #         project_root + f'/{location}/yaml_sources/{object_name}_model.yaml',
    #         project_root + f'/{location}/schemas/generated_universal_tables_schema_for_{svc_name}.py',
    #     )


def get_service_names():
    service_names = []
    service_config = configuration("services")
    for service in service_config["services"]:
        service_names.append(service if isinstance(service, str) else list(service.keys())[0])
    return service_names


def is_git_dirty(repo_path='.'):
    try:
        # Otvaranje repozitorijuma
        repo = git.Repo(repo_path)

        # Proveravanje da li postoje lokalne promene
        if repo.is_dirty(untracked_files=True):
            return True
        return False

    except Exception as e:
        return False


@click.group(context_settings=dict(help_option_names=['-h', '--help'], max_content_width=150))
def do():
    pass

@do.command('new-service')
@click.option('--service-name', '-s', help='Service name to generate or reset')
@click.option('--service-template', '-t', default='base4service_template', help='See list of templates with `bmanager list-templates')
@click.option('--verbose', '-v', is_flag=True, default=False, help='Verbose output')
@click.option('--gen-type', '-g', default='models,schemas', help='Components to generate (comma-separated: models,schemas,tables)')
def new_service(service_name, service_template, verbose, gen_type):
    """
    Create new service
    """
    v = '> /dev/null 2>&1' if verbose else ''

    if not service_name:
        print(f'[*] please provide service name')
        return

    # check is service already exists
    directory = Path(project_root + f'/src/services/{service_name}')
    if directory.is_dir():
        sys.exit(f'[*] service -> {service_name} already exists')

    if is_git_dirty():
        print(f'[*] please commit previous changes!')
        os.system('git status')
        return

    if service_template:
        def _base4emails(service_name):
            os.system(
                f'''
                mkdir -p {project_root}/src/services/sendmail
                git clone https://github.com/base4services/base4sendmail.git {v}
                cd base4sendmail
                git checkout {branch}
                cd ..
                cp -R base4sendmail/services/template/* {project_root}/src/services/sendmail
                cp -R base4sendmail/tests/test_sendmail.py {project_root}/tests/test_sendmail.py
                cp -R base4sendmail/shared/services/* {project_root}/src/shared/services/
                pip3 install -r base4sendmail/requirements.txt #-q
                cat base4sendmail/requirements.txt >> requirements.txt
                rm -rf base4sendmail
                '''
            )
            compile_main_config(service_name, gen_items=gen_type.split(','))

        def _base4tenants(service_name):
            os.system(
                f'''
                mkdir -p {project_root}/src/services/{service_name}
                git clone https://github.com/base4services/base4tenants.git {v}
                cd base4tenants
                git checkout {branch}
                cd ..
                cp -R base4tenants/src/services/tenants/* {project_root}/src/services/{service_name}/
                cp -R base4tenants/tests/test_base_tenants.py {project_root}/tests/
                cp -R base4tenants/tests/test_tenants.py {project_root}/tests/test_tenants.py
                cp -R base4tenants/shared/services/* {project_root}/src/shared/services/
                cat base4tenants/requirements.txt >> requirements.txt
                pip3 install -r base4tenants/requirements.txt #-q
                rm -rf base4tenants
                '''
            )
            compile_main_config(service_name, gen_items=gen_type.split(','))


        def _base4service_template(service_name):
            print('[*] creating service from default template...')
            os.system(
                f'''
                mkdir -p {project_root}/src/services/{service_name}
                git clone https://github.com/base4services/base4service_template.git {v}
                cd base4service_template
                git checkout {branch}
                cd ..
                cp -R base4service_template/services/template/* {project_root}/src/services/{service_name}
                cp base4service_template/tests/test_template.py {project_root}/tests/test_{service_name}.py

                cp base4service_template/rename.sh {project_root}

                bash {project_root}/rename.sh {service_name} src/services
                bash {project_root}/rename.sh {service_name} tests

                rm -rf base4service_template
                rm  {project_root}/rename.sh

                cd {project_root}/src/services/{service_name}
                mv {project_root}/src/services/{service_name}/yaml_sources/model.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_model.yaml
                mv {project_root}/src/services/{service_name}/yaml_sources/schema.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_schema.yaml
                '''
            )
            print(f'[*] service -> {service_name} created!')
            compile_main_config(service_name, gen_items=gen_type.split(','))


        if '@' not in service_template:
            branch = 'main'
        else:
            service_template, branch = service_template.split('@')
            
        if service_template not in existing_service_templates:
            print(f'[*] please choose template')
            for i, j in enumerate(existing_service_templates, start=1):
                print(f'->: {j}')
            return

        if 'base4tenants' in service_template:
            _base4tenants('tenants')
            _base4emails('sendmail')


        elif 'base4service_template' in service_template:
            _base4service_template(service_name)

        else:
            print(f'[*] please choose template')
            for i, j in enumerate(existing_service_templates, start=1):
                print(f'->: {j}')
            return

        _compile_yaml(yaml_file='gen.yaml', service_name=service_name, gen_type=gen_type)
        yaml_to_env('env')
        update_config_ac()


@do.command('reset-service')
@click.option('--service-name', '-s', help='Service name to generate or reset')
def reset_service(service_name):
    """
    Reset service
    """
    os.system('git checkout .')
    try:
        shutil.rmtree(project_root + f'/src/services/{service_name}')
        os.remove(project_root + f'/tests/test_{service_name}.py')
        sys.exit(f'[*] service -> {service_name} files are reset.')
    except Exception as e:
        pass
    
@do.command('compile-ac')
def compile_ac():
    """
    Register all API handlers to access control at config/ac.yaml
    """
    update_config_ac()
    print(f'[*] ac.yaml configuration updated!')
    
@do.command('compile-env')
def compile_env():
    """
    Compile .env from config/env.yaml
    """
    yaml_to_env('env')
    print(f'[*] {project_root}/.env configuration generated!')

@do.command('list-templates')
def list_templates():
    """
    List available service templates
    """
    for i, j in enumerate(existing_service_templates, start=1):
        print(f'->: {j}')

@do.command('aerich')
@click.option('--aerich', '-a', help='aerich command to execute')
@click.option('--service_name', '-s', help='service')
def perform_aerich(aerich, service_name):
    """
    Perform aerich migration
    """
    if aerich not in ('init', 'init-db', 'migrate', 'upgrade', 'downgrade'):
        print(f'[*] please provide valid aerich command')
        return

    for service in ['aerich'] + get_service_names():
        if service_name and service != service_name:
            continue
        print('aerich --app '+service+' '+aerich)

@do.command('test')
def do_test():
    """
    Run all tests
    """
    os.system(
                f'''
            cd {project_root}
            TEST_DATABASE=sqlite pytest -n 8 --disable-warnings tests --no-cov
            cd -
            '''
            )

@do.command('pip-up')
def pip_up():
    """
    Upgrade all PIP packages
    """
    return p_up()

@do.command('pip-down')
def pip_down():
    """
    Downgrade all PIP packages
    """
    return p_down()


@do.command('base-lib-update')
def base_lib_update():
    """
    Update base4 library
    """
    print('[*] Updating base4 library...')
    try:
        os.system(f'''cd {project_root}/.venv/lib/{'python' + sys.version[:4]}/site-packages/base4 && git pull''')
    except:
        pass
    try:
        os.system(f'''cd {project_root}/lib/base4 && git pull''')
    except:
        pass
@do.command('fmt')
def fmt():
    """
    Run black and isort tools for code formatting
    """
    os.system(f'black --target-version py312 --line-length 160 --skip-string-normalization {project_root}')
    os.system(f'isort {project_root} --profile black --line-length 160')
    return

@do.command('init-db')
def initdb():
    """
        Create database and user from env variables
    """
    db_user = os.getenv('DB_POSTGRES_USER')
    password = os.getenv('DB_POSTGRES_PASSWORD')
    test_db = os.getenv('DB_TEST')

    with open(project_root + '/config/env.yaml', 'r') as f:
        db = yaml.safe_load(f)
        os.system(f'psql -U {db_user}` -d template1 -c "CREATE ROLE {db_user} WITH CREATEDB LOGIN PASSWORD \'{password}\';"')
        os.system(f'psql -U {db_user} -d template1 -c "create database {test_db};"')
        for d in db['db']['postgres']['databases']:
            print(f'[*] Creating database {d}')
            os.system(f'psql -U {db_user} -d template1 -c "create database {d};"')


@do.command('services')
def services():
    """
        List available services
    """
    print(f'[*] Available services:')
    for i, j in enumerate(get_service_names(), start=1):
        print(j)
    return


def _compile_yaml(yaml_file: str, service_name: str, gen_type: str):

    try:
        _yaml_file = (project_root + '/config/' + yaml_file) if '/' not in yaml_file else yaml_file
        with open(_yaml_file) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f'Error loading {_yaml_file}')
        print(e)
        return

    if data and 'services' in data and isinstance(data['services'], list):
        for i in data['services']:
            svc_name = i['name']

            if service_name and svc_name not in service_name:
                continue

            location = i['location']

            if not gen_type:
                to_gen = i.get('gen')
            else:
                to_gen = gen_type

            gen4svc(svc_name, location, gen=to_gen)


@do.command('compile-yaml')
@click.option('--yaml-file', '-y', default='gen.yaml', help='YAML file to use for generation')
@click.option('--service-name', '-s', help='Service name')
@click.option('--gen-type', '-g', default='models,schemas', help='Components to generate (comma-separated: models,schemas,tables)')
def compile_yaml(yaml_file: str, service_name: str, gen_type: str):
    """
    Compile config/gen.yaml
    """
    _compile_yaml(yaml_file, service_name, gen_type)


# if __name__ == '__main__':
#     _compile_yaml('gen.yaml','hotels','schemas')
# ...
