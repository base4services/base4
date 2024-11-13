#!/usr/bin/env python3

import os
import shutil
import sys
from pathlib import Path

import asyncclick as click
import git
import yaml

import base4.scripts.gen_model as gen_model
import base4.scripts.gen_schemas as gen_schemas
import base4.scripts.gen_tables as gen_tables
from base4 import configuration
from base4.scripts.pip.down import do as p_down
from base4.scripts.pip.up import do as p_up
from base4.utilities.config import yaml_to_env
from base4.utilities.files import get_project_root

project_root = str(get_project_root())


def gen4svc(svc_name, object_name, location, gen=None):
	if not gen:
		gen = {'models', 'schemas', 'tables'}
	if 'models' in gen:
		gen_model.save(
			project_root + f'/{location}/yaml_sources/{object_name}_model.yaml',
			project_root + f'/{location}/models/generated_{object_name}_model.py',
		)
	if 'schemas' in gen:
		gen_schemas.save(
			project_root + f'/{location}/yaml_sources/{object_name}_schema.yaml',
			project_root + f'/{location}/schemas/generated_{object_name}_schema.py',
		)
	
	if 'tables' in gen:
		gen_tables.save(
			svc_name,
			project_root + f'/{location}/yaml_sources/{object_name}_table.yaml',
			project_root + f'/{location}/yaml_sources/{object_name}_model.yaml',
			project_root + f'/{location}/schemas/generated_universal_tables_schema_for_{svc_name}.py',
		)


def get_service_names():
	service_names = []
	service_config = configuration("services")
	for service in service_config["services"]:
		service_names.append(list(service.keys())[0])
	return service_names


def evaluate_gen(gen: str):
	gen_values = gen.split(",")
	for gen in gen_values:
		print('-', gen)
		if gen not in ("schemas", "tables", "models"):
			raise ValueError("gen must be one of 'schemas', 'tables', 'models' or 'models'")
	return gen_values


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
@click.option('--gen', '-g', help='Components to generate (comma-separated: models,schemas,tables)')
@click.option('--pip-up', '-pu', is_flag=True, help='pip upgrade')
@click.option('--pip-down', '-pd', is_flag=True, help='pip downgrade')
@click.option('--fmt', '-f', is_flag=True, help='Run format and isort recursively')
@click.option('--ls-templates', '-lt', is_flag=True, help='List available templates')
@click.option('--template', '-t', help='Choose template: (-t base4tenants ...)')
@click.option('--base-lib-update', '-u', is_flag=True, help='Update base4 library')
@click.pass_context
def do(ctx, new_service, reset_service, compile_env, compile_yaml, gen, pip_up, pip_down, fmt, ls_templates, template, base_lib_update):
	if not any([new_service, reset_service, compile_env, compile_yaml, pip_up, pip_down, fmt, ls_templates, template, base_lib_update]):
		click.echo(ctx.get_help())
		return
	
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
		for i, j in enumerate(['base4ws', 'base4tenants', 'base4sendmail'], start=1):
			print(f'{i}: {j}')
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
			sys.exit(f'[*] please commit previous changes!')
		
		if template:
			if template == 'base4tenants':
				os.system(f'''
				mkdir -p {project_root}/src/services/{new_service}
				git clone git+ssh://git@github2/base4services/base4tenants.git > /dev/null 2>&1
				cp -R base4tenants/* {project_root}/src/services/{new_service}
				rm -rf base4tenants
				''')
			elif template == 'base4ws':
				os.system(f'''
				git clone git+ssh://git@github2/base4services/base4tenants.git > /dev/null 2>&1
				mv base4ws/ws {project_root}/src
				rm -rf base4ws
				''')
			elif template == 'base4sendmail':
				os.system(f'''
				mkdir -p {project_root}/src/services/sendmail
				git clone git+ssh://git@github2/base4services/base4sendmail.git > /dev/null 2>&1
				cp -R sendmail/* {project_root}/src/services/sendmail
				rm -rf sendmail
				''')
				
			os.system(f'craft -s {new_service} > /dev/null 2>&1')
			
		else:
			# compile yaml files
			os.system(f'craft -s {new_service} > /dev/null 2>&1')
	
	if gen:
		gen = evaluate_gen(gen)
	
	try:
		yaml_file = (project_root + '/config/' + compile_yaml) if '/' not in compile_yaml else compile_yaml
		with open(yaml_file) as f:
			data = yaml.safe_load(f)
	except Exception as e:
		print(f'Error loading {compile_yaml}')
		print(e)
		return

	if data and 'services' in data:
		for i in data['services']:
			svc_name = i['name']
			if new_service and svc_name not in new_service:
				continue
			singular_name = i['singular']
			
			location = i['location']
			
			if not gen:
				to_gen = i.get('gen')
			else:
				to_gen = gen
			gen4svc(svc_name, singular_name, location, gen=to_gen)
			
			# run test for new service
			os.system(f'pytest -n 8 --disable-warnings {project_root + f"/tests/test_{new_service}.py"}')


if __name__ == '__main__':
	do()
