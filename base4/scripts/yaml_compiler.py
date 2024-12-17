import importlib
import inspect
import os
from base4.utilities.files import get_project_root

project_root = get_project_root()


def update_config_db(db_name: str):
	with open(project_root / 'config/db.yaml', 'r') as f:
		content = f.read()
	
	content = content.replace("'", "")
	
	new_db_section = f"""
db_{db_name}: &db_{db_name}
  <<: *db
  database: ${{DB_{db_name.upper()}}}
"""
	
	new_connection_section = f"""
    conn_{db_name}:
      engine: tortoise.backends.asyncpg
      credentials: *db_{db_name}
"""
	
	new_app_section = f"""
    {db_name}:
      models:
        - services.{db_name}.models
      default_connection: conn_{db_name}
"""
	
	if 'tortoise:' in content:
		content = content.replace('tortoise:', new_db_section + '\ntortoise:')
	
	if 'connections:' in content:
		content = content.replace('connections:', 'connections:' + new_connection_section)
	
	if 'apps:' in content:
		content = content.replace('apps:', 'apps:' + new_app_section)
	
	with open(project_root / 'config/db.yaml', 'w') as f:
		f.write(content)


def update_config_services(service_name: str):
	with open(project_root / 'config/services.yaml', 'r') as f:
		content = f.read()
	
	content = content.replace("'", "")
	
	new_service_line = f"  - {service_name}\n"
	
	if 'services:' in content:
		if new_service_line not in content:
			content = content.replace('services:\n', 'services:\n' + new_service_line)
	else:
		content += f"\nservices:\n{new_service_line}"
	
	with open(project_root / 'config/services.yaml', 'w') as f:
		f.write(content)


def update_config_gen(service_name: str, gen_items: list):
	# Učitaj postojeći sadržaj fajla kao string
	with open(project_root / 'config/gen.yaml', 'r') as f:
		content = f.read()
	
	content = content.replace("'", "")
	
	if f"  - name: {service_name}" in content:
		print(f"Service '{service_name}' already exists in the configuration.")
		return
	
	gen_section = "\n".join([f"      - {item}" for item in gen_items])
	new_block = f"""
  - name: {service_name}
    singular: {service_name}
    location: src/services/{service_name}
    gen:
{gen_section}
"""
	
	if 'services:' in content:
		content = content.replace('services:\n', 'services:\n' + new_block)
	else:
		content += f"\nservices:\n{new_block}"
	
	with open(project_root / 'config/gen.yaml', 'w') as f:
		f.write(content)


def update_config_env(service_name: str):
	with open(project_root / 'config/env.yaml', 'r') as f:
		content = f.read()
	
	content = content.replace("'", "")
	new_service_line = f"      - {service_name}\n"
	
	if 'databases:' in content:
		if new_service_line not in content:
			content = content.replace('databases:\n', 'databases:\n' + new_service_line)
	else:
		content += f"\ndatabases:\n{new_service_line}"
	
	# Snimi ažurirani sadržaj nazad u fajl
	with open(project_root / 'config/env.yaml', 'w') as f:
		f.write(content)


def update_config_ac():
	for service in os.listdir(f"{project_root}/src/services"):
		if os.path.isdir(f"{project_root}/src/services/{service}"):
			if os.path.exists(f"{project_root}/src/services/{service}/api/handlers.py"):
				module = importlib.import_module(f'services.{service}.api.handlers')
				for api_handler in inspect.getmembers(module):
					try:
						instance = api_handler[1]
						if hasattr(instance, 'router'):
							print('router found')
					except Exception as e:
						pass
	# for service in sel
	# # with open(project_root / 'config/ac.yaml', 'w') as f:
	# 	f.write(content)
	
	
def compile_main_config(service_name: str, gen_items: list):
	update_config_gen(service_name, gen_items)
	update_config_services(service_name)
	update_config_db(service_name)
	update_config_env(service_name)
