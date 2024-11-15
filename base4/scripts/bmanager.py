#!/usr/bin/env python3

import os
import shutil
import sys
from pathlib import Path

import asyncclick as click
import git
import yaml

from base4 import configuration
from base4.scripts.pip.down import do as p_down
from base4.scripts.pip.up import do as p_up
from base4.utilities.config import yaml_to_env
from base4.utilities.files import get_project_root
from base4.scripts.yaml_compiler import compile_main_config

import base4.scripts.gen_model as gen_model
import base4.scripts.gen_schemas as gen_schemas
import base4.scripts.gen_tables as gen_tables

project_root = str(get_project_root())


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
        service_names.append(list(service.keys())[0])
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


@click.command(context_settings=dict(help_option_names=['-h', '--help'], max_content_width=150))  # Širina 80 karaktera)
@click.option('--new-service', '-s', help='Service name to generate')
@click.option('--reset-service', '-r', is_flag=True, help='Reset compiled files from newly created service')
@click.option('--compile-env', '-e', is_flag=True, help=f'Generate .env file from env.yaml')
@click.option('--compile-yaml', '-y', default='gen.yaml', help='YAML file to use for generation')
@click.option('--gen-type', '-g', default='model,schema', help='Components to generate (comma-separated: models,schemas,tables)')
@click.option('--pip-up', '-pu', is_flag=True, help='pip upgrade')
@click.option('--pip-down', '-pd', is_flag=True, help='pip downgrade')
@click.option('--fmt', '-f', is_flag=True, help='Run format and isort recursively')
@click.option('--ls-templates', '-lt', is_flag=True, help='List available templates')
@click.option('--template', '-t', default='base4service_template', help='See  list of templates with `bmanager -lt` ')
@click.option('--base-lib-update', '-u', is_flag=True, help='Update base4 library')
@click.pass_context
def do(ctx, new_service, reset_service, compile_env, compile_yaml, gen_type, pip_up, pip_down, fmt, ls_templates, template, base_lib_update):

    if not any([new_service, reset_service, compile_env, pip_up, pip_down, fmt, ls_templates, base_lib_update]):
        click.echo(ctx.get_help())
        return
    # todo ako je -s i g onda regenerisi samo taj servis
    # todo validacija za g parametar
    if base_lib_update:
        print('[*] Updating base4 library...')
        os.system(f'''cd {project_root}/lib/base4 && git pull''')
        return

    if fmt:
        os.system(f'black --target-version py312 --line-length 160 --skip-string-normalization {project_root}')
        os.system(f'isort {project_root} --profile black --line-length 160')
        return

    if pip_down:
        return p_down()

    elif pip_up:
        return p_up()

    if compile_env:
        yaml_to_env('env')
        print(f'[*] {project_root}/.env configuration generated!')
        return

    if ls_templates:
        for i, j in enumerate(['base4tenants', 'base4ws', 'base4sendmail', 'base4service_template'], start=1):
            print(f'->: {j}')
        return

    if new_service:
        # reset project logic
        if reset_service and new_service:
            os.system('git checkout .')
            try:
                shutil.rmtree(project_root + f'/src/services/{new_service}')
                os.remove(project_root + f'/tests/test_{new_service}.py')
                sys.exit(f'[*] service -> {new_service} files are reset.')
            except Exception as e:
                pass
            return

        # check is service already exists
        directory = Path(project_root + f'/src/services/{new_service}')
        if directory.is_dir():
            sys.exit(f'[*] service -> {new_service} already exists')

        if is_git_dirty():
            print(f'[*] please commit previous changes!')
            os.system('git status')
            return

        if template:
            if template == 'base4tenants':
                os.system(
                    f'''
				mkdir -p {project_root}/src/services/{new_service}
				git clone git+ssh://git@github2/base4services/base4tenants.git > /dev/null 2>&1
				cp -R base4tenants/src/services/tenants/* {project_root}/src/services/{new_service}/
				cp -R base4tenants/tests/test_tenants.py {project_root}/tests/test_base_{new_service}.py
				rm -rf base4tenants
				'''
                )
            elif template == 'base4ws':
                os.system(
                    f'''
				git clone git+ssh://git@github2/base4services/base4ws.git > /dev/null 2>&1
				cp -R base4ws/ws {project_root}/src
				rm -rf base4ws
				'''
                )
            elif template == 'base4sendmail':
                os.system(
                    f'''
				mkdir -p {project_root}/src/services/sendmail
				git clone git+ssh://git@github2/base4services/base4sendmail.git > /dev/null 2>&1
				cp -R sendmail/* {project_root}/src/services/sendmail
				rm -rf sendmail
				'''
                )
            elif template == 'base4service_template':
                print('[*] creating service from default template...')
                os.system(
                    f'''
				echo [*] creating service -> {new_service}
				mkdir -p {project_root}/src/services/{new_service}
				git clone git+ssh://git@github2/base4services/base4service_template.git > /dev/null 2>&1
				cp -R base4service_template/* {project_root}/src/services/{new_service}
				rm -rf base4service_template {new_service}
				cd {project_root}/src/services/{new_service}
				bash rename.sh {new_service}
				rm  {project_root}/src/services/{new_service}/rename.sh
				mv {project_root}/src/services/{new_service}/yaml_sources/model.yaml {project_root}/src/services/{new_service}/yaml_sources/{new_service}_model.yaml
				mv {project_root}/src/services/{new_service}/yaml_sources/schema.yaml {project_root}/src/services/{new_service}/yaml_sources/{new_service}_schema.yaml
				'''
                )
                print(f'[*] service -> {new_service} created!')
                
            else:
                print(f'[*] please choose template')
                for i, j in enumerate(['base4tenants', 'base4ws', 'base4sendmail', 'base4service_template'], start=1):
                    print(f'->: {j}')
                return
            
            # generate main config yaml
            compile_main_config(new_service, gen_items=gen_type.split(','))

        else:
            print(f'[*] please choose template')
            for i, j in enumerate(['base4tenants', 'base4ws', 'base4sendmail', 'base4service_template'], start=1):
                print(f'->: {j}')
            return

    try:
        yaml_file = (project_root + '/config/' + compile_yaml) if '/' not in compile_yaml else compile_yaml
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f'Error loading {compile_yaml}')
        print(e)
        return

    if data and 'services' in data and isinstance(data['services'], list):
        for i in data['services']:
            svc_name = i['name']
            if new_service and svc_name not in new_service:
                continue
            location = i['location']

            if not gen_type:
                to_gen = i.get('gen')
            else:
                to_gen = gen_type
                
            gen4svc(svc_name, location, gen=to_gen)

            # run test for new service
            os.system(f'pytest -n 8 --disable-warnings {project_root + f"/tests/test_{new_service}.py"} --no-cov')


if __name__ == '__main__':
    do()
