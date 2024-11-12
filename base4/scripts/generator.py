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
@click.option('--yaml_file', '-y', default='gen.yaml', help='YAML file to use for generation')
@click.option('--service', '-s', help='Service name to generate')
@click.option('--gen', '-g', help='Components to generate (comma-separated: models,schemas,tables)')
@click.option('--reset', '-r', is_flag=True, help='Reset compiled files from newly created service')
@click.option('--env', '-e', is_flag=True, help=f'Generate .env file from {project_root}/env.yaml')
@click.pass_context
def main(ctx, yaml_file, service: None, gen=None, reset=None, env=None):
	# Proveravamo da li su sve opcije na podrazumevanim vrednostima
	if all(value in [None, 'gen.yaml', False, False] for value in ctx.params.values()):
		click.echo(ctx.get_help())
		ctx.exit()
	
	if env:
		yaml_to_env('env')
		print(f'[*] {project_root}/.env configuration generated!')
		return
	
	if service:
		# reset project logic
		if reset and service:
			os.system('git checkout .')
			try:
				shutil.rmtree(project_root + f'/src/services/{service}')
				os.remove(project_root + f'/tests/test_{service}.py')
				sys.exit(f'[*] service -> {service} files are reset.')
			except Exception as e:
				pass
			return
		
		# check is service already exists
		directory = Path(project_root + f'/src/services/{service}')
		if directory.is_dir():
			sys.exit(f'[*] service -> {service} already exists')
		
		if is_git_dirty():
			sys.exit(f'[*] please commit previous changes!')
			
		# compile yaml files
		os.system(f'craft -s {service}')
	
	if gen:
		gen = evaluate_gen(gen)

	try:
		yaml_file = (project_root + '/config/' + yaml_file) if '/' not in yaml_file else yaml_file
		with open(yaml_file) as f:
			data = yaml.safe_load(f)
	except Exception as e:
		print(f'Error loading {yaml_file}')
		print(e)
		return
	
	for i in data['services']:
		svc_name = i['name']
		if service and svc_name not in service:
			continue
		singular_name = i['singular']
		
		location = i['location']
		
		if not gen:
			to_gen = i.get('gen')
		else:
			to_gen = gen
		gen4svc(svc_name, singular_name, location, gen=to_gen)
	
	# run test for new service
	os.system(f'pytest -n 8 --disable-warnings {project_root + f"/tests/test_{service}.py"}')
	
	
if __name__ == '__main__':
	main()
