import importlib
import time as ttime
from datetime import datetime, time
from ipaddress import ip_address, ip_network

from base4.utilities.config import load_yaml_config

_module_cache = {}
rate_limit_cache = {}


def _preprocess_roles(roles_config):
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
		
		parent_role = role.get("inherits")
		if parent_role:
			if isinstance(parent_role, str):
				parent_role = [parent_role]
			
			parent_permissions = []
			parent_attributes = set()
			parent_rate_limit = {}
			for pr in parent_role:
				parent_result = merge_permissions(pr)
				parent_permissions.extend(parent_result["permissions"])
				parent_attributes.update(parent_result["attributes"])
				for k, v in parent_result["rate_limit"].items():
					parent_rate_limit[k] = v
			
			all_permissions = parent_permissions + permissions
			
			unique_permissions = {}
			for p in all_permissions:
				unique_permissions[p["name"]] = p
			permissions = list(unique_permissions.values())
			
			global_attributes = parent_attributes.union(global_attributes)
			
			merged_rate_limit = dict(parent_rate_limit)
			merged_rate_limit.update(global_rate_limit)
			global_rate_limit = merged_rate_limit
		
		final_permissions = []
		for p in permissions:
			final_attrs = set(global_attributes).union(p["attributes"])
			
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
		
		merged_roles[role_name] = {
			"permissions": final_permissions,
			"attributes":  list(global_attributes),
			"rate_limit":  global_rate_limit,
			"middlewares": []
		}
		return merged_roles[role_name]
	
	for role_name in roles_config:
		merge_permissions(role_name)
	
	return merged_roles


def _evaluate_attribute(attr_name, context, attributes):
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
	obj_class = type(obj)
	return f"{obj_class.__module__}.{obj_class.__name__}"


def is_rate_limited(api_handler, session, rate_limit):
	current_time = int(ttime.time())
	cache_key = f"{session.user_id}:{session.role}:{api_handler}"
	data = rate_limit_cache.get(cache_key)
	
	period = rate_limit["period"]
	max_calls = rate_limit["calls"]
	
	if data is None:
		rate_limit_cache[cache_key] = {"calls": 1, "start_time": current_time}
		return False
	
	start_time = data["start_time"]
	calls = data["calls"]
	
	if current_time - start_time > period:
		data["calls"] = 1
		data["start_time"] = current_time
		return False
	
	if calls >= max_calls:
		return True
	
	data["calls"] = calls + 1
	return False


def _parse_middlewares_config(MIDDLEWARES):
	mw_dict = {}
	known_keys = {"function"}
	
	for mw_item in MIDDLEWARES:
		mw_name = None
		function_str = None
		
		for key, value in mw_item.items():
			if key not in known_keys:
				mw_name = key
				function_str = value
		
		if mw_name is None:
			raise ValueError("MIDDWARE_NAME_NOT_FOUND")
		
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


def _apply_middleware(current_user, middlewares_list, MIDDLEWARES):
	for mw_name in middlewares_list:
		mw_data = MIDDLEWARES.get(mw_name)
		if not mw_data:
			raise ValueError(f"MIDDLEWARE '{mw_name}' NOT_FOUND")
		mw_func = _import_middleware_function(mw_data["function"])
		return mw_func(current_user)


AC_CONFIG = load_yaml_config("ac")
API_HANDLERS = AC_CONFIG.get("api_handlers", {})
ROLES = _preprocess_roles(AC_CONFIG["roles"])
ATTRIBUTES = AC_CONFIG.get("attributes", {})
MIDDLEWARES = _parse_middlewares_config(AC_CONFIG.get("middlewares", []))
