from base4.utilities.files import get_project_root

project_root = get_project_root()


def update_config_db(db_name: str):
	# Učitaj postojeći sadržaj fajla kao string
	with open(project_root / 'config/db.yaml', 'r') as f:
		content = f.read()
	
	# Ukloni jednostruke navodnike iz celog sadržaja
	content = content.replace("'", "")
	
	# Kreiraj novi deo za bazu sa sidrom i merđ ključem u obliku stringa
	new_db_section = f"""
db_{db_name}: &db_{db_name}
  <<: *db
  database: ${{DB_{db_name.upper()}}}
"""
	
	# Kreiraj novu sekciju za tortoise.connections
	new_connection_section = f"""
    conn_{db_name}:
      engine: tortoise.backends.asyncpg
      credentials: *db_{db_name}
"""
	
	# Kreiraj novu sekciju za tortoise.apps
	new_app_section = f"""
    {db_name}:
      models:
        - services.{db_name}.models
      default_connection: conn_{db_name}
"""
	
	# Umetni novi deo za bazu pre 'tortoise:' sekcije
	if 'tortoise:' in content:
		content = content.replace('tortoise:', new_db_section + '\ntortoise:')
	
	# Umetni novu konekciju u sekciju 'connections' unutar 'tortoise'
	if 'connections:' in content:
		content = content.replace('connections:', 'connections:' + new_connection_section)
	
	# Umetni novu aplikaciju u sekciju 'apps' unutar 'tortoise'
	if 'apps:' in content:
		content = content.replace('apps:', 'apps:' + new_app_section)
	
	# Snimi ažurirani sadržaj nazad u fajl
	with open(project_root / 'config/db.yaml', 'w') as f:
		f.write(content)


def update_config_services(service_name: str):
	# Učitaj postojeći sadržaj fajla kao string
	with open(project_root / 'config/services.yaml', 'r') as f:
		content = f.read()
	
	# Ukloni jednostruke navodnike iz celog sadržaja
	content = content.replace("'", "")
	
	# Kreiraj liniju za novi servis
	new_service_line = f"  - {service_name}\n"
	
	# Proveri da li sekcija 'services' postoji
	if 'services:' in content:
		# Ako sekcija postoji, proveri da li servis već postoji
		if new_service_line not in content:
			# Dodaj novi servis u postojeću 'services' sekciju
			content = content.replace('services:\n', 'services:\n' + new_service_line)
	else:
		# Ako sekcija ne postoji, dodaj novu sekciju 'services' sa prvim servisom
		content += f"\nservices:\n{new_service_line}"
	
	# Snimi ažurirani sadržaj nazad u fajl
	with open(project_root / 'config/services.yaml', 'w') as f:
		f.write(content)


def update_config_gen(service_name: str, gen_items: list):
	# Učitaj postojeći sadržaj fajla kao string
	with open(project_root / 'config/gen.yaml', 'r') as f:
		content = f.read()
	
	# Ukloni jednostruke navodnike iz celog sadržaja
	content = content.replace("'", "")
	
	# Proveri da li blok sa ovim 'name' već postoji
	if f"  - name: {service_name}" in content:
		print(f"Service '{service_name}' already exists in the configuration.")
		return
	
	# Kreiraj string za novi blok
	gen_section = "\n".join([f"      - {item}" for item in gen_items])
	new_block = f"""
  - name: {service_name}
    singular: {service_name}
    location: src/services/{service_name}
    gen:
{gen_section}
"""
	
	# Proveri da li sekcija 'services:' postoji
	if 'services:' in content:
		# Dodaj novi blok na kraj sekcije 'services'
		content = content.replace('services:\n', 'services:\n' + new_block)
	else:
		# Ako 'services:' ne postoji, dodaj novu sekciju
		content += f"\nservices:\n{new_block}"
	
	# Snimi ažurirani sadržaj nazad u fajl
	with open(project_root / 'config/gen.yaml', 'w') as f:
		f.write(content)


def compile_main_config(service_name: str, gen_items: list):
	update_config_gen(service_name, gen_items)
	update_config_services(service_name)
	update_config_db(service_name)
