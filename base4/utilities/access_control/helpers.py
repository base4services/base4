import yaml
import os
from functools import wraps
from datetime import datetime, time
from ipaddress import ip_network, ip_address
import time as ttime
import importlib

# Keš za module da izbegnemo višestruki import istog modula u _import_middleware_function
_module_cache = {}

# Keš za rate limit, ključ = user:role:handler, vrednost = {"calls": X, "start_time": epoch}
rate_limit_cache = {}


def load_config(yaml_file: str):
	"""Učitaj YAML konfiguraciju iz fajla."""
	with open(yaml_file, "r") as file:
		return yaml.safe_load(file)


def _preprocess_roles(roles_config):
	"""
	Preprocesiraj role tako da se sve nasleđene permisije, atributi i rate-limiti
	"flatten-u" u jednu finalnu strukutru za svaku rolu.
	"""
	merged_roles = {}
	def merge_permissions(role_name):
		if role_name in merged_roles:
			return merged_roles[role_name]
		
		role = roles_config.get(role_name)
		if role is None:
			raise ValueError(f"{role_name} ROLE_NOT_FOUND")
		
		_attributes = role.get("attributes", [])
		global_attributes = set(_attributes) if _attributes else set()
		global_rate_limit = role.get("rate_limit", {})
		role_permissions = role.get("permissions", [])
		
		permissions = []
		# Obradi trenutnu rolu i spakuj permisije
		for perm in role_permissions:
			if isinstance(perm, str):
				# Nema lokalnog override-a
				permissions.append(
					{
						"name":        perm,
						"attributes":  list(global_attributes),
						"rate_limit":  global_rate_limit,
						"middlewares": []
					}
				)
			else:
				# perm je dict tipa {"ime.permisije": {"attributes": [...], "rate_limit": {...}, "middlewares": [...]}}
				for key, value in perm.items():
					local_attrs = value.get("attributes", [])
					merged_attrs = global_attributes.union(local_attrs)
					local_rate_limit = value.get("rate_limit", global_rate_limit)
					local_middlewares = value.get("middlewares", [])
					permissions.append(
						{
							"name":        key,
							"attributes":  list(merged_attrs),
							"rate_limit":  local_rate_limit,
							"middlewares": local_middlewares
						}
					)
		
		# Ako postoji inherit, rekurzivno spoji.
		parent_role = role.get("inherits")
		if parent_role:
			# parent_role može biti lista ili string; pretpostavimo da je uvek lista radi jasnoće
			# Ako nije lista, napravi je
			if isinstance(parent_role, str):
				parent_role = [parent_role]
			
			# Spajanje svih parent rola
			parent_permissions = []
			parent_attributes = set()
			parent_rate_limit = {}
			for pr in parent_role:
				parent_result = merge_permissions(pr)
				parent_permissions.extend(parent_result["permissions"])
				parent_attributes.update(parent_result["attributes"])
				# Merge rate limit-a: parent -> child
				for k, v in parent_result["rate_limit"].items():
					parent_rate_limit[k] = v
			
			# Spoji parent i trenutne permisije
			all_permissions = parent_permissions + permissions
			
			# Ukloni duplicirane permisije po imenu - kasnije navedene imaju prioritet
			unique_permissions = {}
			for p in all_permissions:
				unique_permissions[p["name"]] = p
			permissions = list(unique_permissions.values())
			
			# Atributi
			global_attributes = parent_attributes.union(global_attributes)
			
			# Rate limit - global u roli
			merged_rate_limit = dict(parent_rate_limit)
			merged_rate_limit.update(global_rate_limit)
			global_rate_limit = merged_rate_limit
		
		# Finalno obradi sve permisije sa globalnim atributima i spojenim rate limitima
		final_permissions = []
		for p in permissions:
			# Spajanje globalnih atributa i onih iz permisije
			final_attrs = set(global_attributes).union(p["attributes"])
			
			# Rate-limit
			p_rl = dict(global_rate_limit)
			p_rl.update(p["rate_limit"])
			
			final_permissions.append(
				{
					"name":        p["name"],
					"attributes":  list(final_attrs),
					"rate_limit":  p_rl,
					"middlewares": p["middlewares"]
				}
			)
		
		# Zapamti rezultat
		merged_roles[role_name] = {
			"permissions": final_permissions,
			"attributes":  list(global_attributes),
			"rate_limit":  global_rate_limit,
			"middlewares": []
		}
		return merged_roles[role_name]
	
	# Preprocesiraj sve role
	for role_name in roles_config:
		merge_permissions(role_name)
	
	return merged_roles


def _evaluate_attribute(attr_name, context, attributes):
	"""
	Evaluiraj pojedinačni atribut na osnovu njegovog tipa i parametara.
	"""
	c_time = context.get("current_time")
	if c_time is None:
		c_time = datetime.now().time()
	
	c_ip = context.get("client_ip", "0.0.0.0")
	
	if attr_name.startswith("time_based"):
		return _evaluate_time_based(attr_name, c_time, attributes)
	elif attr_name.startswith("location_based"):
		return _evaluate_location_based(attr_name, c_ip, attributes)
	return False


def _evaluate_time_based(attr_name, current_time, attributes):
	"""
	Evaluiraj time_based atribut.
	Očekuje da je attr_name formata "time_based.<ime_atributa>".
	"""
	time_based_config = attributes.get("time_based", [])
	if not time_based_config:
		return False
	
	attr_key = attr_name.split(".", 1)[1]
	# Pretvori u dict za brzi lookup
	tba_dict = {attr["name"]: attr["params"] for attr in time_based_config}
	condition = tba_dict.get(attr_key)
	if condition is None:
		return False
	
	from_time = time.fromisoformat(condition[0]["from"])
	to_time = time.fromisoformat(condition[1]["to"])
	return from_time <= current_time <= to_time


def _evaluate_location_based(attr_name, client_ip, attributes):
	"""
	Evaluiraj location_based atribut.
	Očekuje da je attr_name formata "location_based.<ime_atributa>".
	"""
	location_based_config = attributes.get("location_based", [])
	if not location_based_config:
		return False
	
	attr_key = attr_name.split(".", 1)[1]
	lba_dict = {attr["name"]: attr["params"] for attr in location_based_config}
	condition = lba_dict.get(attr_key)
	if condition is None:
		return False
	
	network = ip_network(condition["cidr"])
	return ip_address(client_ip) in network


def _get_api_handler_class_path(obj):
	"""Vrati class path instance API handler-a u formatu: module.ClassName"""
	obj_class = type(obj)
	return f"{obj_class.__module__}.{obj_class.__name__}"


def is_rate_limited(api_handler, user_id, role, rate_limit):
	"""
	Proveri da li je korisnik prekoračio broj poziva za zadati api_handler, user_id i rolu.
	"""
	current_time = int(ttime.time())
	cache_key = f"{user_id}:{role}:{api_handler}"
	data = rate_limit_cache.get(cache_key)
	
	period = rate_limit["period"]
	max_calls = rate_limit["calls"]
	
	if data is None:
		rate_limit_cache[cache_key] = {"calls": 1, "start_time": current_time}
		return False
	
	start_time = data["start_time"]
	calls = data["calls"]
	
	# Reset ako je period istekao
	if current_time - start_time > period:
		data["calls"] = 1
		data["start_time"] = current_time
		return False
	
	# Ako smo prekoračili broj poziva
	if calls >= max_calls:
		return True
	
	data["calls"] = calls + 1
	return False


def _parse_middlewares_config(middlewares_config):

	mw_dict = {}
	known_keys = {"function"}
	
	for mw_item in middlewares_config:
		mw_name = None
		function_str = None
		
		for key, value in mw_item.items():
			if key not in known_keys:
				# Pretpostavimo da je to ime middleware-a
				mw_name = key
				function_str = value
		
		if mw_name is None:
			raise ValueError("Nisam pronašao ime middleware-a u jednom od middleware definicija.")
		
		mw_entry = {"function": function_str}
		mw_dict[mw_name] = mw_entry
	
	return mw_dict


def _import_middleware_function(func_str):
	module_name, func_name = func_str.rsplit(":", 1)
	mod = _module_cache.get(module_name)
	if mod is None:
		mod = importlib.import_module(module_name)
		_module_cache[module_name] = mod
	return getattr(mod, func_name)


def _apply_middleware(current_user, middlewares_list, middlewares_dict):
	"""
	Primeni middlewares u redosledu kako su navedeni.
	Ako neki middleware vrati False ili digne grešku,
	prekida se obrada.
	"""
	for mw_name in middlewares_list:
		mw_data = middlewares_dict.get(mw_name)
		if not mw_data:
			raise ValueError(f"MIDDLEWARE '{mw_name}' NOT_FOUND")
		
		mw_func = _import_middleware_function(mw_data["function"])
		return mw_func(current_user)
	

# Putanja do config fajla
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ac.yaml")
config = load_config(config_path)
api_handlers = config.get("api_handlers", {})
roles = _preprocess_roles(config["roles"])
attributes_config = config.get("attributes", {})
middlewares_config = config.get("middlewares", [])
middlewares_dict = _parse_middlewares_config(middlewares_config)


def api():
	"""
	Dekorator za API endpoint metode.
	Validira permisije, atribute, middlewares i rate-limit pre poziva originalne funkcije.
	"""
	
	def decorator(func):
		@wraps(func)
		def wrapper(api_instance, *args, **kwargs):
			func_name = func.__name__
			class_path = _get_api_handler_class_path(api_instance)
			full_api_handler_class_path = f"{class_path}.{func_name}"
			api_module_name = full_api_handler_class_path.split(".", 1)[0]
			
			api_handler = api_handlers.get(api_module_name)
			if api_handler is None:
				raise ValueError(f"API handler for method '{func_name}' not found in configuration.")
			
			current_user = api_instance.current_user
			current_role = current_user["role"]
			user_id = current_user["id"]
			
			role_config = roles.get(current_role)
			if role_config is None:
				raise PermissionError(f"Permission '{func_name}' denied for role '{current_role}'.")
			
			permissions = role_config["permissions"]
			target_permission_name = f"{api_module_name}.{func_name}"
			
			permission = None
			for perm in permissions:
				if perm["name"] == target_permission_name:
					permission = perm
					break
			
			if permission is None:
				raise PermissionError(f"Permission '{func_name}' denied for role '{current_role}'.")
			
			context = kwargs.get("context", {})
			
			# Evaluacija atributa
			for attr in permission.get("attributes", []):
				if not _evaluate_attribute(attr, context, attributes_config):
					raise PermissionError(f"Attribute conditions not satisfied for role '{current_role}'.")
			
			# Middlewares
			permission_middlewares = permission.get("middlewares", [])
			if permission_middlewares:
				if not _apply_middleware(current_user, permission_middlewares, middlewares_dict):
					raise PermissionError(f"Middleware error occurred for role '{current_role}'.")
			
			# Rate limit
			p_rl = permission.get("rate_limit") or role_config.get("rate_limit")
			if p_rl and is_rate_limited(api_handler, user_id, current_role, p_rl):
				raise PermissionError(f"Rate limit exceeded for role '{current_role}'.")
			
			return func(api_instance, *args, **kwargs)
		
		return wrapper
	
	return decorator
