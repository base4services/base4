import dotenv

from base4.utilities.files import get_project_root

dotenv.load_dotenv(get_project_root() / '.env')

import inspect
import os
import uuid
from typing import Any, Dict, List, TypeVar

from fastapi import HTTPException, Request
from tortoise import Tortoise

from base4.utilities.config import load_yaml_config

SchemaType = TypeVar('SchemaType')


current_file_path = str(get_project_root())


TORTOISE_ORM = load_yaml_config('db')['tortoise']


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


class BaseServiceDbUtils:
    @staticmethod
    async def db_operations(base_service_instance, request: Request, body: dict, payload: SchemaType, logged_user_id: uuid.UUID, m2m_relations: dict, _conn):
        """
        Perform database operations for creating an item.

        This method orchestrates the entire process of creating an item,
        including handling m2m relations, caching, and post-save operations.
        """
        _conn = BaseServiceDbUtils._get_connection(_conn)

        await BaseServiceDbUtils._process_schema_fields(base_service_instance, payload, body, m2m_relations, logged_user_id, request, _conn)

        item = await BaseServiceDbUtils._create_and_save_item(base_service_instance, body, logged_user_id, _conn)

        await BaseServiceDbUtils._handle_m2m_relations(item, m2m_relations)

        await BaseServiceDbUtils._handle_caching(base_service_instance, item, logged_user_id, request, _conn)

        await BaseServiceDbUtils._execute_post_save_hook(payload, base_service_instance, body, request)

        return item

    @staticmethod
    def _get_connection(_conn):
        """Determine the appropriate database connection."""
        if os.getenv('TEST_MODE', None) in ('True', 'true', '1', True) and os.getenv('TEST_DATABASE', None) == 'sqlite':
            # This will kill transactions in sqlite and test mode

            return None

        return _conn

    @staticmethod
    async def _process_schema_fields(
        base_service_instance, payload: SchemaType, body: dict, m2m_relations: dict, logged_user_id: uuid.UUID, request: Request, _conn
    ):
        """Process each field in the schema, handling lists and m2m relations."""
        for key, _value in base_service_instance.model.schema_loc_dict.items():
            try:
                value = eval(f'payload.{_value}')
                if value == '__NOT_SET__':
                    continue
                if isinstance(value, List):
                    await BaseServiceDbUtils._handle_list_field(base_service_instance, key, value, m2m_relations, logged_user_id, request, _conn)
                else:
                    body[key] = value
            except Exception:
                continue

    @staticmethod
    async def _handle_list_field(base_service_instance, key: str, value: List, m2m_relations: dict, logged_user_id: uuid.UUID, request: Request, _conn):
        """Handle list fields, creating related objects if necessary."""
        service_loc = base_service_instance.model.schema_service_loc()
        for list_item in value:
            if isinstance(list_item, dict):
                raise NameError("Use Schem Type instead dict in List")

            try:
                res = await BaseServiceDbUtils._create_or_update_related_item(base_service_instance, key, list_item, service_loc, logged_user_id, request, _conn)
            except Exception as e:
                raise

            if key not in m2m_relations:
                m2m_relations[key] = []
            m2m_relations[key].append(res)

    @staticmethod
    async def _create_or_update_related_item(
        base_service_instance, key: str, list_item: Any, service_loc: Dict, logged_user_id: uuid.UUID, request: Request, _conn
    ):
        """Create or update a related item based on existence rules."""
        if key in base_service_instance.schema.check_existence_rules():
            update_if_exists_key_fields = base_service_instance.schema.check_existence_rules()[key]
            existence_rule = base_service_instance.schema.check_existence_rules()[key]
            update_if_exists_value_fields = [getattr(list_item, fld) for fld in existence_rule]
            return await service_loc[key](request).create(
                logged_user_id,
                list_item,
                request,
                update_if_exists=True,
                update_if_exists_key_fields=update_if_exists_key_fields,
                update_if_exists_value_fields=update_if_exists_value_fields,
                conn=_conn,
                return_db_object=True,
            )
        else:
            return await service_loc[key](request).create(logged_user_id, list_item, request, **list_item.unq(), return_db_object=True)

    @staticmethod
    async def _create_and_save_item(base_service_instance, body: dict, logged_user_id: uuid.UUID, _conn):
        """Create and save the main item."""
        item = base_service_instance.model(logged_user_id, **body)
        await item.save(using_db=_conn)
        return item

    @staticmethod
    async def _handle_m2m_relations(item, m2m_relations: dict):
        """Handle many-to-many relations."""
        if m2m_relations:
            for key, value in m2m_relations.items():
                await getattr(item, key).add(*value)

    @staticmethod
    async def _handle_caching(base_service_instance, item, logged_user_id: uuid.UUID, request: Request, _conn):
        """Handle caching operations."""
        if base_service_instance.c11:
            cache11 = base_service_instance.c11(**{base_service_instance.c11_related_to: item})
            await cache11.save(using_db=_conn)
            await base_service_instance.mk_cache(request, 'c11', cache11, item, _conn)

        if base_service_instance.c1n:
            cache1n = base_service_instance.c1n(language='en', **{base_service_instance.c1n_related_to: item})
            await cache1n.save(using_db=_conn)

    @staticmethod
    async def _execute_post_save_hook(payload: SchemaType, base_service_instance, body: dict, request: Request):
        """Execute the post-save hook if it exists."""
        if hasattr(payload, 'post_save') and inspect.ismethod(getattr(payload, 'post_save')):
            try:
                if not await getattr(payload, 'post_save')(svc=base_service_instance, db_id=body['id'], request=request, body=body, payload=payload):
                    raise HTTPException(
                        status_code=400, detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_save", "message": f"post_save method failed"}
                    )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_save", "message": f"Error in post_save method: {str(e)}"},
                )


##########################################################################################
# coupled version
# import inspect
# import os
# import uuid
# from typing import List, TypeVar
#
# from fastapi import HTTPException, Request
#
# SchemaType = TypeVar('SchemaType')
#
#
# # TODO continue with refactor, decouple logic blocks
# class BaseServiceDbUtils:
#     @staticmethod
#     async def db_operations(base_service_instance, request: Request, body: dict, payload: SchemaType, logged_user_id: uuid.UUID, m2m_relations: dict, _conn):
#         if os.getenv('TEST_MODE', None) in ('True', 'true', '1', True) and os.getenv('TEST_DATABASE', None) == 'sqlite':
#             _conn = None
#         else:
#             _conn = _conn
#
#         for key, _value in base_service_instance.model.schema_loc_dict.items():
#
#             try:
#                 value = eval(f'payload.{_value}')
#
#                 if value == '__NOT_SET__':
#                     continue
#
#                 if isinstance(value, List):
#
#                     for list_item in value:
#
#                         if isinstance(list_item, dict):
#                             raise NameError("Use Schem Type instead dict in List")
#
#                         service_loc = base_service_instance.model.schema_service_loc()
#
#                         # TODO:
#                         # try get if this item already exists
#                         # don't create new one
#
#                         if key in base_service_instance.schema.check_existence_rules():
#                             update_if_exists_key_fields = base_service_instance.schema.check_existence_rules()[key]
#                             existence_rule = base_service_instance.schema.check_existence_rules()[key]
#                             update_if_exists_value_fields = [getattr(list_item, fld) for fld in existence_rule]
#                             res = await service_loc[key]().create(
#                                 logged_user_id,
#                                 list_item,
#                                 request,
#                                 update_if_exists=True,
#                                 update_if_exists_key_fields=update_if_exists_key_fields,
#                                 update_if_exists_value_fields=update_if_exists_value_fields,
#                                 conn=_conn,
#                                 return_db_object=True,
#                             )
#
#                             ...
#                         else:
#                             res = await service_loc[key]().create(logged_user_id, list_item, request, **list_item.unq(), return_db_object=True)
#
#                         if key not in m2m_relations:
#                             m2m_relations[key] = []
#
#                         m2m_relations[key].append(res)
#
#                         ...
#
#                     continue
#
#                 body[key] = value
#             except Exception as e:
#                 continue
#
#         item = base_service_instance.model(logged_user_id, **body)
#
#         await item.save(using_db=_conn)
#
#         if m2m_relations:
#             for key, value in m2m_relations.items():
#                 await getattr(item, key).add(*value)
#
#         if base_service_instance.c11:
#             cache11 = base_service_instance.c11(
#                 # logged_user_id
#                 **{
#                     # 'idx_created_by': logged_user_id, 'idx_last_updated_by': logged_user_id,
#                     base_service_instance.c11_related_to: item
#                 }
#             )
#             await cache11.save(using_db=_conn)
#
#             await base_service_instance.mk_cache(request, 'c11', cache11, item, _conn)
#
#         if base_service_instance.c1n:
#             cache1n = base_service_instance.c1n(
#                 # logged_user_id,
#                 language='en',
#                 **{base_service_instance.c1n_related_to: item},
#             )
#             await cache1n.save(using_db=_conn)
#
#         if hasattr(payload, 'post_save') and inspect.ismethod(getattr(payload, 'post_save')):
#             try:
#                 if not await getattr(payload, 'post_save')(svc=base_service_instance, db_id=body['id'], request=request, body=body, payload=payload):
#                     # THIS will abort transaction
#                     raise HTTPException(
#                         status_code=400, detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_save", "message": f"post_save method failed"}
#                     )
#             except Exception as e:
#                 # THIS will abort transaction
#                 raise HTTPException(
#                     status_code=400,
#                     detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_save", "message": f"Error in post_save method: {str(e)}"},
#                 )
#
#         return item
