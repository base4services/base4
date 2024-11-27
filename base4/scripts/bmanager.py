#!/usr/bin/env python3

import os
import shutil
import sys
from pathlib import Path

# import asyncclick as click
import click
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


@click.group(context_settings=dict(help_option_names=['-h', '--help'], max_content_width=150))
def do():
    pass

@do.command('new-service')
@click.option('--service-name', '-s', help='Service name to generate or reset')
@click.option('--service-template', '-t', default='base4service_template', help='See list of templates with `bmanager list-templates')
@click.option('--verbose', '-v', is_flag=True, default=False, help='Verbose output')
@click.option('--gen-type', '-g', default='models,schemas', help='Components to generate (comma-separated: models,schemas,tables)')
def new_service(service_name, service_template, verbose, gen_type):
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
        if service_template not in existing_service_templates:
            print(f'[*] please choose template')
            for i, j in enumerate(existing_service_templates, start=1):
                print(f'->: {j}')
            return

        if service_template == 'base4tenants':
            if service_name != 'tenants':
                sys.exit(f'[*] Tenants service name can not be renamed! \nIf you want to create your version of tenants service, use:\n'
                         f'bmanager new-service -s {service_name} -t base4service_template ')
                
            os.system(
                f'''
                mkdir -p {project_root}/src/services/tenants
                git clone git+ssh://git@github2/base4services/base4tenants.git {v}
                cp -R base4tenants/src/services/tenants/* {project_root}/src/services/tenants/
                cp -R base4tenants/tests/test_base_tenants.py {project_root}/tests/
                cp -R base4tenants/tests/test_tenants.py {project_root}/tests/test_tenants.py
                rm -rf base4tenants
                '''
            )
        elif service_template == 'base4ws':
            os.system(
                f'''
                git clone git+ssh://git@github2/base4services/base4ws.git {v}
                cp -R base4ws/ws {project_root}/src
                rm -rf base4ws
                '''
            )
        elif service_template == 'base4sendmail':
            os.system(
                f'''
                mkdir -p {project_root}/src/services/sendmail
                git clone git+ssh://git@github2/base4services/base4sendmail.git {v}
                cp -R sendmail/* {project_root}/src/services/sendmail
                rm -rf sendmail
                '''
            )
        elif service_template == 'base4service_template':
            print('[*] creating service from default template...')
            os.system(
                f'''
                mkdir -p {project_root}/src/services/{service_name}
                git clone git+ssh://git@github2/base4services/base4service_template.git {v}
                cp -R base4service_template/services/template/* {project_root}/src/services/{service_name}
                cp base4service_template/rename.sh {project_root}/src/services/{service_name}
                
                cp base4service_template/tests/test_template.py {project_root}/tests/test_{service_name}.py 
                cp base4service_template/tests/test_api_v2.py {project_root}/tests/test_api_v2_{service_name}.py
                rm -rf base4service_template
                bash rename.sh {service_name}
                cd {project_root}/src/services/{service_name}
                rm  {project_root}/src/services/{service_name}/rename.sh
                mv {project_root}/src/services/{service_name}/yaml_sources/model.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_model.yaml
                mv {project_root}/src/services/{service_name}/yaml_sources/schema.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_schema.yaml
                '''
            )
            print(f'[*] service -> {service_name} created!')

        else:
            print(f'[*] please choose template')
            for i, j in enumerate(existing_service_templates, start=1):
                print(f'->: {j}')
            return

        # generate main config yaml
        compile_main_config(service_name, gen_items=gen_type.split(','))

        # continue with another command
        _compile_yaml(yaml_file='gen.yaml', service_name=service_name, gen_type=gen_type)


@do.command('reset-service')
@click.option('--service-name', '-s', help='Service name to generate or reset')
def new_service(service_name):
    os.system('git checkout .')
    try:
        shutil.rmtree(project_root + f'/src/services/{service_name}')
        os.remove(project_root + f'/tests/test_{service_name}.py')
        sys.exit(f'[*] service -> {service_name} files are reset.')
    except Exception as e:
        pass

@do.command('compile-env')
def compile_env():
    yaml_to_env('env')
    print(f'[*] {project_root}/.env configuration generated!')

@do.command('list-templates')
def list_templates():
    for i, j in enumerate(existing_service_templates, start=1):
        print(f'->: {j}')

@do.command('aerich')
@click.option('--aerich', '-a', help='aerich command to execute')
@click.option('--service_name', '-s', help='service')
def perform_aerich(aerich, service_name):

    if aerich not in ('init', 'init-db', 'migrate', 'upgrade', 'downgrade'):
        print(f'[*] please provide valid aerich command')
        return

    for service in ['aerich'] + get_service_names():
        if service_name and service != service_name:
            continue
        print('aerich --app '+service+' '+aerich)

@do.command('test')
def do_test():
    os.system(
                f'''
            cd {project_root}
            TEST_DATABASE=sqlite pytest -n 8 --disable-warnings tests --no-cov
            cd -
            '''
            )

@do.command('pip-up')
def pip_up():
    return p_up()

@do.command('pip-down')
def pip_down():
    return p_down()


@do.command('base-lib-update')
def base_lib_update():
    print('[*] Updating base4 library...')
    os.system(f'''cd {project_root}/lib/base4 && git pull''')

@do.command('fmt')
def fmt():
    os.system(f'black --target-version py312 --line-length 160 --skip-string-normalization {project_root}')
    os.system(f'isort {project_root} --profile black --line-length 160')
    return

@do.command('services')
def services():
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
    _compile_yaml(yaml_file, service_name, gen_type)

            # run test for new service
            # os.system(f'pytest -n 8 --disable-warnings {project_root + f"/tests/test_{new_service}.py"} --no-cov')





#
# @click.command(context_settings=dict(help_option_names=['-h', '--help'], max_content_width=150))
# @click.option('--command', '-c',
#               type=click.Choice(
#                   ['new-service',
#                    'reset-service',
#                    'compile-env',
#                    'compile-yaml',
#                    # 'gen-from-yaml',
#                    'pip-up',
#                    'pip-down',
#                    'list-templates',
#                    'base-lib-update',
#                    'fmt',
#                    'test',
#                    'services',
#                    'aerich'
#                    ]),
#               required=True,
#               help='Command to execute',
#               )
# @click.option('--aerich', '-a', help='aerich command to execute')
# @click.option('--service-name', '-s', help='Service name to generate or reset')
# @click.option('--service-template', '-t', default='base4service_template', help='See list of templates with `bmanager -c list-templates')
# @click.option('--yaml-file', '-y', default='gen.yaml', help='YAML file to use for generation')
# @click.option('--gen-type', '-g', default='models,schemas', help='Components to generate (comma-separated: models,schemas,tables)')
# @click.option('--verbose', '-v', is_flag=True, default=False, help='Verbose output')
#
# def do(command, aerich, service_name, yaml_file, service_template, gen_type, verbose):
#
#     #TODO: ovo pokupiti listanjem git repo-a
#     existing_service_templates = ['base4tenants', 'base4ws', 'base4sendmail', 'base4service_template']
#     v = '> /dev/null 2>&1' if verbose else ''
#
#     if command == 'base-lib-update':
#         print('[*] Updating base4 library...')
#         os.system(f'''cd {project_root}/lib/base4 && git pull''')
#         return
#
#     if command == 'fmt':
#         os.system(f'black --target-version py312 --line-length 160 --skip-string-normalization {project_root}')
#         os.system(f'isort {project_root} --profile black --line-length 160')
#         return
#
#     if command == 'services':
#         print(f'[*] Available services:')
#         for i, j in enumerate(get_service_names(), start=1):
#             print(j)
#         return
#
#     if command == 'aerich':
#         if not aerich:
#             print(f'[*] please provide aerich command')
#             return
#
#         if aerich not in ('init', 'init-db', 'migrate', 'upgrade', 'downgrade'):
#             print(f'[*] please provide valid aerich command')
#             return
#
#         for service in ['aerich'] + get_service_names():
#             if service_name and service != service_name:
#                 continue
#             print('aerich --app '+service+' '+aerich)
#
#     if command == 'test':
#         os.system(
#             f'''
#         cd {project_root}
#         TEST_DATABASE=sqlite pytest -n 8 --disable-warnings tests --no-cov
#         cd -
#         '''
#         )
#         return
#
#     if command == 'pip-down':
#         return p_down()
#
#     if command == 'pip-up':
#         return p_up()
#
#     if command == 'compile-env':
#         yaml_to_env('env')
#         print(f'[*] {project_root}/.env configuration generated!')
#         return
#
#     if command == 'list-templates':
#         for i, j in enumerate(existing_service_templates, start=1):
#             print(f'->: {j}')
#         return
#
#     if command == 'reset-service':
#
#         if not service_name:
#             print(f'[*] please provide service name')
#             return
#
#         os.system('git checkout .')
#         try:
#             shutil.rmtree(project_root + f'/src/services/{service_name}')
#             os.remove(project_root + f'/tests/test_{service_name}.py')
#             sys.exit(f'[*] service -> {service_name} files are reset.')
#         except Exception as e:
#             pass
#         return
#
#     if command == 'new-service':
#
#         if not service_name:
#             print(f'[*] please provide service name')
#             return
#
#         # check is service already exists
#         directory = Path(project_root + f'/src/services/{service_name}')
#         if directory.is_dir():
#             sys.exit(f'[*] service -> {service_name} already exists')
#
#         if is_git_dirty():
#             print(f'[*] please commit previous changes!')
#             os.system('git status')
#             return
#
#         # if service_template:
#         #     if service_template not in existing_service_templates:
#         #         print(f'[*] please choose template')
#         #         for i, j in enumerate(existing_service_templates, start=1):
#         #             print(f'->: {j}')
#         #         return
#         #
#         #     if service_template == 'base4tenants':
#         #         os.system(
#         #             f'''
# 		# 		mkdir -p {project_root}/src/services/{service_name}
# 		# 		git clone git+ssh://git@github2/base4services/base4tenants.git {v}
# 		# 		cp -R base4tenants/src/services/tenants/* {project_root}/src/services/{service_name}/
# 		# 		cp -R base4tenants/tests/test_base_tenants.py {project_root}/tests/
# 		# 		cp -R base4tenants/tests/test_tenants.py {project_root}/tests/test_{service_name}.py
# 		# 		cp -R base4tenants/rename.sh {project_root}/src/services/{service_name}
# 		# 		rm -rf base4tenants
#         #         cd {project_root}/src/services/{service_name}
# 		# 		bash rename.sh {service_name}
# 		# 		rm  {project_root}/src/services/{service_name}/rename.sh
# 		# 		mv {project_root}/src/services/{service_name}/yaml_sources/tenants_model.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_model.yaml
# 		# 		mv {project_root}/src/services/{service_name}/yaml_sources/tenants_schema.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_schema.yaml
# 		# 		mv {project_root}/src/services/{service_name}/api/tenants.py {project_root}/src/services/{service_name}/api/{service_name}.py
# 		# 		mv {project_root}/src/services/{service_name}/schemas/tenants.py {project_root}/src/services/{service_name}/schemas/{service_name}.py
# 		# 		'''
#         #         )
#         #     elif service_template == 'base4ws':
#         #         os.system(
#         #             f'''
# 		# 		git clone git+ssh://git@github2/base4services/base4ws.git {v}
# 		# 		cp -R base4ws/ws {project_root}/src
# 		# 		rm -rf base4ws
# 		# 		'''
#         #         )
#         #     elif service_template == 'base4sendmail':
#         #         os.system(
#         #             f'''
# 		# 		mkdir -p {project_root}/src/services/sendmail
# 		# 		git clone git+ssh://git@github2/base4services/base4sendmail.git {v}
# 		# 		cp -R sendmail/* {project_root}/src/services/sendmail
# 		# 		rm -rf sendmail
# 		# 		'''
#         #         )
#         #     elif service_template == 'base4service_template':
#         #         print('[*] creating service from default template...')
#         #         os.system(
#         #             f'''
# 		# 		mkdir -p {project_root}/src/services/{service_name}
# 		# 		git clone git+ssh://git@github2/base4services/base4service_template.git {v}
# 		# 		cp -R base4service_template/services/template/* {project_root}/src/services/{service_name}
#         #         cp base4service_template/rename.sh {project_root}/src/services/{service_name}
#         #         cp base4service_template/tests/test_template.py {project_root}/tests/test_{service_name}.py
# 		# 		rm -rf base4service_template
# 		# 		cd {project_root}/src/services/{service_name}
# 		# 		bash rename.sh {service_name}
# 		# 		rm  {project_root}/src/services/{service_name}/rename.sh
# 		# 		mv {project_root}/src/services/{service_name}/yaml_sources/model.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_model.yaml
# 		# 		mv {project_root}/src/services/{service_name}/yaml_sources/schema.yaml {project_root}/src/services/{service_name}/yaml_sources/{service_name}_schema.yaml
# 		# 		'''
#         #         )
#         #         print(f'[*] service -> {service_name} created!')
#         #
#         #     else:
#         #         print(f'[*] please choose template')
#         #         for i, j in enumerate(existing_service_templates, start=1):
#         #             print(f'->: {j}')
#         #         return
#         #
#         #     # generate main config yaml
#         #     compile_main_config(service_name, gen_items=gen_type.split(','))
#         #
#         #     # continue with another command
#         #     command = 'compile-yaml'
#
#     if command == 'compile-yaml':
#
#         try:
#             _yaml_file = (project_root + '/config/' + yaml_file) if '/' not in yaml_file else yaml_file
#             with open(_yaml_file) as f:
#                 data = yaml.safe_load(f)
#         except Exception as e:
#             print(f'Error loading {_yaml_file}')
#             print(e)
#             return
#
#         if data and 'services' in data and isinstance(data['services'], list):
#             for i in data['services']:
#                 svc_name = i['name']
#
#                 if service_name and svc_name not in service_name:
#                     continue
#
#                 location = i['location']
#
#                 if not gen_type:
#                     to_gen = i.get('gen')
#                 else:
#                     to_gen = gen_type
#
#                 gen4svc(svc_name, location, gen=to_gen)
#
# # if __name__ == '__main__':
# #     do()
