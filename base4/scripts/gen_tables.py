import datetime
import os

import yaml


def gen_profile(table, profile_name, profile, model_definition):
    schema_name = f'{table.capitalize()}{profile_name.capitalize()}Schema'

    model_columns = {}

    def get_fields(root):
        nonlocal model_columns
        for field in root:
            if field.startswith('__'):
                continue

            try:
                _field = root[field] if type(root[field]) == str else root[field]['field']
            except Exception as e:
                raise

            model_columns[field] = _field

    get_fields(model_definition)
    if '__cache11' in model_definition:
        get_fields(model_definition['__cache11'])

    if '__cache1n' in model_definition:
        get_fields(model_definition['__cache1n'])

    res = f'class {schema_name}(UniversalTableResponseBaseSchema):\n'

    order = []
    order_map = {}
    sortable = set()
    filterable = set()
    column2width = {}
    column2justify = {}
    column2title = {}

    meta = {}

    if '__post_get' in profile:
        res += f'\n\t@staticmethod\n'
        res += f'\tasync def post_get(svc, data, request, _request: Request):\n'
        res += f'\t\treturn await getattr(svc,\"{profile["__post_get"]}\")(data, request, _request)\n\n'

    for _field in profile['columns']:

        _field_name = _field

        if isinstance(_field, dict):
            field_name = list(_field.keys())[0]

        if field_name == '__meta':
            meta = _field
            continue

        db_field_type = model_columns[field_name] if field_name in model_columns else ''

        widths = [100, 100, 100]

        if isinstance(_field, dict):
            if 'sortable' in _field[field_name] and _field[field_name]['sortable']:
                sortable.add(field_name)

                if 'order_by' in _field[field_name]:
                    order_map[field_name] = _field[field_name]['order_by']
                else:
                    order_map[field_name] = field_name

            if 'filterable' in _field[field_name] and _field[field_name]['filterable']:
                filterable.add(field_name)
            if 'widths' in _field[field_name]:
                widths = _field[field_name]['widths']

        justify = 'start'
        if 'justify' in _field[field_name] and _field[field_name]['justify']:
            justify = _field[field_name]['justify']

        column2width[field_name] = widths

        column2justify[field_name] = justify

        column2title[field_name] = _field[field_name]['title'] if 'title' in _field[field_name] else field_name

        field_type = 'Any'

        if 'fields.Int' in db_field_type:
            field_type = 'int'
        elif 'fields.Text' in db_field_type or 'fields.Char' in db_field_type:
            field_type = 'str'

        res += f'\t{field_name} : {field_type}\n'
        order.append(field_name)

    res += f'\n\t@staticmethod\n'
    res += f'\tdef order():\n'
    res += f'\t\treturn {order}\n\n'
    res += f'\n\t@staticmethod\n'
    res += f'\tdef sortable(field:str):\n'

    sortable = str(list(sortable)).replace('[', '{').replace(']', '}')
    res += f'\t\treturn field in {sortable}\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef order_map():\n'
    res += f'\t\treturn {order_map}\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef filterable(field:str):\n'

    filterable = str(list(filterable)).replace('[', '{').replace(']', '}')
    res += f'\t\treturn field in {filterable}\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef filter_properties(field:str):\n'
    m = {}
    for i in profile['columns']:
        k = list(i.keys())[0]
        if 'filterable' in i[k] and i[k]['filterable']:
            if isinstance(i[k]['filterable'], bool):
                m[k] = {'enabled': i[k]['filterable']}
            else:
                m[k] = i[k]['filterable']
    res += f'\t\tm = {m}\n\n'
    res += f'\t\treturn m.get(field,False)\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef column_data_type(field:str):\n'
    m = {}
    for i in profile['columns']:
        k = list(i.keys())[0]
        if 'type' in i[k] and i[k]['type']:
            m[k] = i[k]['type']
    res += f'\t\tm = {m}\n\n'
    res += f'\t\treturn m.get(field)\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef column2width():\n'
    res += f'\t\treturn {column2width}\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef column2justify():\n'
    res += f'\t\treturn {column2justify}\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef column2title():\n'
    res += f'\t\treturn {column2title}\n\n'

    res += f'\n\t@staticmethod\n'
    res += f'\tdef meta():\n'
    res += f'\t\treturn {meta}\n\n'

    return res


def generate(svc_name, fname, model_fname):
    with open(model_fname, 'rt') as f:
        model_definition = yaml.safe_load(f)
    with open(fname, 'rt') as f:
        conf = yaml.safe_load(f)

    res = f'''# THIS IS AN AUTO-GENERATED AND PROTECTED FILE. PLEASE USE
# THE gen_tables.py SCRIPT TO GENERATE THIS FILE. DO NOT EDIT DIRECTLY
# AS IT CAN BE OVERWRITTEN. 
#
# FILE GENERATED ON: {datetime.datetime.now()}

import uuid, datetime

from fastapi import Request

from typing import List, Dict, Optional, AnyStr, Any

from base4.schemas.universal_table import UniversalTableResponseBaseSchema

'''

    try:

        for profile_name in list(conf['profiles']):
            profile = conf['profiles'][profile_name]
            model_name = profile['model']
            try:
                mod_def = model_definition[model_name]
            except Exception as e:
                print("USE ONE OF ",model_definition.keys())
                raise
            try:
                res += gen_profile(svc_name, profile_name, profile, mod_def)
            except Exception as e:
                raise
            ...

    except Exception as e:
        print(e)
        raise
    return res


def save(svc_name, input_yaml, model_input_yaml, gen_fname):
    res = generate(svc_name, input_yaml, model_input_yaml)

    os.system(f'rm -rf {gen_fname}')

    with open(gen_fname, 'wt') as f:
        f.write(res)

    os.system(f'isort {gen_fname} --line-length 160 ')

    os.system(f'black --target-version py312 --line-length 160 --skip-string-normalization {gen_fname}')

    os.system(f'chmod 444 {gen_fname}')

    # with open(gen_fname, 'rt') as f:
    #     print(f.read())
