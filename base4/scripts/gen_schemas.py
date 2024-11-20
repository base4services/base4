import os
import datetime

import yaml


def extract_type(s):
    if 'Optional' not in s:
        return s

    s = s.split('[')[1].split(']')[0].strip()
    if '|' in s:
        s = s.split('|')[0].strip()

    if '=' in s:
        s = s.split('=')[0].strip()

    return s


def gen_schema_particles(tbl, tbl_name):
    res = ''
    for s in tbl['__schema_particles']:
        model_loc = None
        schema_class_loc = {}

        res += f'\nclass {s}(Base):\n'
        for field in tbl['__schema_particles'][s]:
            if field == 'model_loc':
                model_loc = tbl['__schema_particles'][s][field]
                continue

            schema_class_loc[field] = extract_type(tbl['__schema_particles'][s][field])

            res += f'\t{field}: {tbl["__schema_particles"][s][field]}\n'

        if model_loc:
            res += f'\t@classmethod\n'
            res += f'\tdef model_loc(cls):\n\t\treturn {model_loc}\n'

        if schema_class_loc:
            # res += f'\t@classmethod\n'
            # res += f'\tdef schema_class_loc(cls):\n\t\treturn {schema_class_loc}\n'
            res += f'\t@classmethod\n'
            res += '\tdef schema_class_loc(cls):\n\t\treturn {\n'
            for field in schema_class_loc:
                res += f'\t\t\t"{field}": {schema_class_loc[field]},\n'
            res += '}'

        res += '\n'
    return res


def gen_schema(tbl, tbl_name):
    schemas = tbl['__schemas']

    res = ''
    high_level_order_starts_from = 999999

    check_existence_per_item = {}

    for s in schemas:

        res += f'\nclass {schemas[s]}(Base):\n'

        ordered_fields = []

        schema_class_loc = {}

        model_loc = {
            'created': 'created',
            'last_updated': 'last_updated',
            'is_deleted': 'is_deleted',
            'deleted': 'deleted',
            'id': 'id',
        }

        for field in tbl:
            high_level_order_starts_from += 1

            if field.startswith('__'):
                continue

            if 'schemas' not in s or s in tbl[field]['schemas']:

                field_name = field
                if 'schema_field_name' in tbl[field]:
                    field_name = tbl[field]['schema_field_name']

                order_index = int(tbl[field]['schema_order_index']) if 'schema_order_index' in tbl[field] else high_level_order_starts_from
                if 'mandatory' in tbl[field] and not tbl[field]['mandatory']:
                    if tbl[field].get('default'):
                        ordered_fields.append((order_index, f'\t{field_name}: Optional[{tbl[field]['type']} | None ]= {tbl[field]['default']}\n'))
                    else:
                        ordered_fields.append((order_index, f'\t{field_name}: Optional[{tbl[field]['type']} | None | Literal[NOT_SET]] = NOT_SET\n'))
                else:
                    if 'Optional' in tbl[field]['type']:
                        raise ValueError(f'Optional should not be in schema_field: {tbl[field]['type']}')
                    ordered_fields.append((order_index, f'\t{field_name}: {tbl[field]['type']}\n'))
                # res +=

                if 'check_existence' in tbl[field]:
                    check_existence_per_item[field] = tbl[field]['check_existence']

                schema_class_loc[field] = tbl[field]['type']

                if 'org_unit' in field:  # _display_name' in field:
                    ...  # debugging

                if 'model' in tbl[field]:
                    model_loc[field] = tbl[field]['model']
                else:
                    model_loc[field] = field

        if len(ordered_fields) == 0:
            res += '\tpass\n'
        else:
            try:
                ordered_fields.sort(key=lambda x: x[0])
            except Exception as e:
                raise
            for field in ordered_fields:
                res += field[1]

        res += '\n'

        res += f'\t@classmethod\n'
        res += f'\tdef check_existence_rules(cls):\n\t\treturn {check_existence_per_item}\n'

        if model_loc:
            res += f'\t@classmethod\n'
            res += f'\tdef model_loc(cls):\n\t\treturn {model_loc}\n'

        res += '\n'

        if schema_class_loc:
            res += f'\t@classmethod\n'
            res += '\tdef schema_class_loc(cls):\n\t\treturn {\n'
            for field in schema_class_loc:
                res += f'\t\t\t"{field}": {schema_class_loc[field]},\n'
            res += '}'

        if '__on_change_value' in tbl:
            res += f'\n\tasync def on_change_value(self, key, new_value, old_value, svc, item, request: Request, logged_user_id: uuid.UUID):\n'
            res += f'\t\ttry:\n'

            for key in tbl['__on_change_value']:
                res += f'\t\t\tif key == "{key}":\n'
                res += f'\t\t\t\treturn await svc.{tbl["__on_change_value"][key]}(data=self, new_value=new_value, old_value=old_value, item=item, request=request, logged_user_id=logged_user_id)\n'
                res += f'\n'
            res += f'\t\texcept Exception as e:'
            res += f'\t\t\traise'

        if '__pre_save_create' in tbl:
            res += f'\n\tasync def pre_save_create(self, svc, db_id: uuid.UUID, request: Request, body: Dict, payload):\n'
            res += f'\t\ttry:'
            res += f'\t\t\treturn await svc.{tbl["__pre_save_create"]}(data=self, db_id=db_id, request=request, body=body, payload=payload)\n'
            res += f'\t\texcept Exception as e:'
            res += f'\t\t\traise'

        if '__pre_save_update' in tbl:
            res += f'\n\tasync def pre_save_update(self, svc, db_id: uuid.UUID, request: Request, body: Dict, payload):\n'
            res += f'\t\ttry:'
            res += f'\t\t\treturn await svc.{tbl["__pre_save_update"]}(data=self, db_id=db_id, request=request, body=body, payload=payload)\n'
            res += f'\t\texcept Exception as e:'
            res += f'\t\t\traise'

        if '__post_save' in tbl:
            res += f'\n\tasync def post_save(self, svc, db_id: uuid.UUID, request: Request, body: Dict, payload):\n'
            res += f'\t\ttry:'
            res += f'\t\t\treturn await svc.{tbl["__post_save"]}(data=self, db_id=db_id, request=request, body=body, payload=payload)\n'
            res += f'\t\texcept Exception as e:'
            res += f'\t\t\traise'

            # res += f'\n\tasync def post_save(self, svc, db_id: uuid.UUID, request: Request):\n'
            # res += f'\t\treturn await svc.{tbl["__post_save"]}(data=self, db_id=db_id, request=request)\n'

        # TODO: add _create in def name
        if '__post_commit_create' in tbl:
            res += f'\n\tasync def post_commit(self, svc, item: Any, request: Request):\n'
            res += f'\t\treturn await svc.{tbl["__post_commit_create"]}(data=self, item=item, request=request)\n'

        if '__post_commit_update' in tbl:
            res += f'\n\tasync def post_commit_update(self, svc, item: Any, updated: Dict, request: Request):\n'
            res += f'\t\treturn await svc.{tbl["__post_commit_update"]}(data=self, item=item, updated=updated, request=request)\n'

        if '__post_get' in tbl:
            res += f'\n\t@staticmethod\n'
            res += f'\n\tasync def post_get(svc, item: Any, request: Request):\n'
            res += f'\t\treturn await svc.{tbl["__post_get"]}(item=item, request=request)\n'

    return res


def gen_schemas(fname):
    with open(fname, 'rt') as f:
        model_definition = yaml.safe_load(f)

    res = f'''# THIS IS AN AUTO-GENERATED AND PROTECTED FILE. PLEASE USE
# THE gen_model.py SCRIPT TO GENERATE THIS FILE. DO NOT EDIT DIRECTLY
# AS IT CAN BE OVERWRITTEN. 
#
# FILE GENERATED ON: {datetime.datetime.now()}

    
import uuid, datetime

from pydantic import BaseModel, field_validator
from typing import List, Dict, Optional, AnyStr, Literal, Any

from fastapi.requests import Request

from base4.schemas.base import Base, NOT_SET

from base4.project_specifics import lookups_module as Lookups

'''
    # REMOVED
    '''
    from pydantic import root_validator
        @root_validator(pre=True)
        def check_fields(cls, values):
            for key, value in values.items():
                if value is NOT_SET:
                    values.pop(key)
            return values
    
    '''

    try:
        for tbl_name in list(model_definition.keys()):
            if '__schema_particles' in model_definition[tbl_name]:
                res += gen_schema_particles(model_definition[tbl_name], tbl_name)

            if '__schemas' in model_definition[tbl_name]:
                res += gen_schema(model_definition[tbl_name], tbl_name)

            if '__unique_key' in model_definition[tbl_name]:
                m = model_definition[tbl_name]["__unique_key"]
                x = '{'
                for key, value in m.items():
                    x += f'"{key}": {value},'
                x += '}'

                res += f'\n\tdef unq(self):\n\t\treturn {x}\n'

            if '__repr' in model_definition[tbl_name]:
                res += f'\n\tdef __str__(self):\n\t\treturn str(self.{model_definition[tbl_name]["__repr"]}) if self.{model_definition[tbl_name]["__repr"]} is not None else None\n'

    except Exception as e:
        print(e)
        raise
    return res


def save(input_yaml, gen_fname):
    res = gen_schemas(input_yaml)

    os.system(f'rm -rf {gen_fname}')

    with open(gen_fname, 'wt') as f:
        f.write(res)

    os.system(f'isort {gen_fname} --line-length 160 ')

    os.system(f'black --target-version py312 --line-length 160 --skip-string-normalization {gen_fname}')

    os.system(f'chmod 444 {gen_fname}')

    # with open(gen_fname, 'rt') as f:
    #     print(f.read())


if __name__ == '__main__':
    current_file_path = os.path.abspath(os.path.dirname(__file__))

    save(
        current_file_path + '/../services/tickets/yaml_sources/ticket_schema.yaml',
        current_file_path + '/../services/tickets/schemas/generated_tickets_schema.py',
    )
