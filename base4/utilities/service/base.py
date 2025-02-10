import datetime
import hashlib
import os
import time
import uuid
from functools import wraps
from inspect import signature
from typing import Any, Callable, Dict, List, Optional, TypeVar

from fastapi.params import Depends
from starlette.middleware.sessions import SessionMiddleware
from urllib3 import request

from base4.schemas.universal_table import UniversalTableGetRequest, UniversalTableResponse
import pydantic
import tortoise
import tortoise.timezone
import ujson as json
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status
import base4.utilities.db.async_redis as async_redis

from base4.schemas.base import NOT_SET
from base4.scripts.yaml_compiler import generate_class_aliases
from base4.utilities.access_control.helpers import (
    AC_CONFIG,
    API_HANDLERS,
    ATTRIBUTES,
    MIDDLEWARES,
    ROLES,
    _apply_middleware,
    _evaluate_attribute,
    _get_api_handler_class_path,
    is_rate_limited, _merge_with_user_permissions,
)

from base4.utilities.files import get_project_root
from base4.utilities.security.jwt import decode_token, decode_token_v3
from base4.utilities.service.startup import service as app, service
from base4.utilities.ws import emit, sio_client_manager

from base4.utilities import base_dotenv
base_dotenv.load_dotenv()

upload_dir = os.getenv('UPLOAD_DIR', '/tmp')

SchemaType = TypeVar('SchemaType', bound=pydantic.BaseModel)
ModelType = TypeVar('ModelType', bound=tortoise.models.Model)


from shared.services.tenants.schemas.me import Me

class BaseServiceUtils:
    @staticmethod
    def validate_update_if_exists_params(
            update_if_exists_key_fields: List[str],
            update_if_exists_value_fields: List[str],
    ) -> None:
        """
        Validate the parameters for updating if a record exists.

        This method checks if the provided key fields and value fields for updating
        existing records are valid. It ensures that both lists are non-empty and have
        the same length.

        Args:
            update_if_exists_key_fields (List[str]): List of key fields to check for existing records.
            update_if_exists_value_fields (List[str]): List of value fields to update for existing records.

        Raises:
            HTTPException: If the validation fails, with a status code of 500 and appropriate error details.

        Returns:
            None
        """
        if not update_if_exists_key_fields or not update_if_exists_value_fields:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "if update_if_exists is True, update_if_exists_key_fields and update_if_exists_value_fields must be set",
                },
            )
        if len(update_if_exists_key_fields) != len(update_if_exists_value_fields):
            raise HTTPException(
                status_code=500,
                detail={"code": "INTERNAL_SERVER_ERROR",
                        "message": "update_if_exists_key_fields and update_if_exists_value_fields must have same length"},
            )

    @staticmethod
    def update_payload_with_user_data(payload: SchemaType, logged_user_id: uuid.UUID) -> None:
        """
        Update the payload with user data if not already set.

        This method updates the 'created_by' and 'last_updated_by' fields of the payload
        with the logged user's ID if these fields are not already set or are set to a default value.

        Args:
            payload (SchemaType): The payload object to be updated. It should have 'created_by'
                                  and 'last_updated_by' attributes.
            logged_user_id (uuid.UUID): The UUID of the logged-in user.

        Returns:
            None

        Note:
            This method modifies the payload object in-place.
            The SchemaType is expected to have 'created_by' and 'last_updated_by' attributes.
        """
        if not payload.created_by or payload.created_by == NOT_SET:
            payload.created_by = logged_user_id

        if not payload.last_updated_by or payload.last_updated_by == NOT_SET:
            payload.last_updated_by = logged_user_id

    @staticmethod
    async def update_payload_with_ids(
            base_service_instance: Any,
            payload: SchemaType,
    ) -> uuid.UUID:
        """
        Update the payload with unique ID and return an ID.

        This method updates the 'unique_id' of the payload if it's not set,
        and either uses an existing 'id' or generates a new UUID.

        Args:
            base_service_instance (Any): An instance of the base service class.
                This should have attributes: model, uid_prefix, uid_alphabet, and uid_total_length.
            payload (SchemaType): The payload object to be updated.
                It may have 'unique_id' and 'id' attributes.

        Returns:
            uuid.UUID: The ID for the payload, either existing or newly generated.

        Note:
            This method may modify the payload object in-place if it has a 'unique_id' attribute.
            The SchemaType is expected to potentially have 'unique_id' and 'id' attributes.
        """
        if hasattr(payload, 'unique_id') and (not payload.unique_id or payload.unique_id == NOT_SET):
            payload.unique_id = await BaseServiceUtils.generate_unique_id(
                model=base_service_instance.model,
                uid_prefix=base_service_instance.uid_prefix,
                uid_alphabet=base_service_instance.uid_alphabet,
                uid_total_length=base_service_instance.uid_total_length,
            )

        if hasattr(payload, 'id') and getattr(payload, 'id') != NOT_SET:
            _id: uuid.UUID = getattr(payload, 'id')
        else:
            _id: uuid.UUID = uuid.uuid4()

        return _id

    @staticmethod
    async def generate_unique_id(
            model: ModelType,
            uid_prefix: str,
            uid_alphabet: str,
            uid_total_length: int,
    ) -> str:
        """
        Generate a unique ID for a given model.

        This method generates a unique ID using the model's gen_unique_id method,
        with specified prefix, alphabet, and length.

        Args:
            model (ModelType): The Tortoise ORM model class to generate the ID for.
            uid_prefix (str): The prefix to use for the unique ID.
            uid_alphabet (str): The alphabet to use for generating the unique ID.
            uid_total_length (int): The total length of the unique ID, including the prefix.

        Returns:
            str: The generated unique ID.

        Raises:
            Any exceptions raised by the model's gen_unique_id method will propagate.

        Note:
            This method attempts to generate a unique ID up to 10 times before giving up.
        """
        return await model.gen_unique_id(
            prefix=uid_prefix, alphabet=uid_alphabet, total_length=uid_total_length, max_attempts=10
        )

    @staticmethod
    def update_body_with_timestamps(payload: SchemaType, body: Dict[str, Any]) -> None:
        """
        Update the body dictionary with timestamp information from the payload.

        This method updates the 'created' and 'last_updated' fields in the body dictionary
        based on the payload object. If these fields are not set in the payload or are set to
        default values, current timestamp is used. All timestamps are ensured to be timezone-aware.

        Args:
            payload (SchemaType): The payload object that may contain 'created' and 'last_updated' attributes.
            body (Dict[str, Any]): The dictionary to be updated with timestamp information.

        Returns:
            None

        Note:
            This method modifies the 'body' dictionary in-place.
            The SchemaType is expected to potentially have 'created' and 'last_updated' attributes.
        """
        if hasattr(payload, 'created') and getattr(payload, 'created') not in (None, NOT_SET):
            body['created'] = getattr(payload, 'created')
            if tortoise.timezone.is_naive(body['created']):
                body['created'] = tortoise.timezone.make_aware(body['created'])
        else:
            body['created'] = tortoise.timezone.make_aware(datetime.datetime.now())

        if hasattr(payload, 'last_updated') and getattr(payload, 'last_updated') not in (None, NOT_SET):
            body['last_updated'] = getattr(payload, 'last_updated')
            if tortoise.timezone.is_naive(body['last_updated']):
                body['last_updated'] = tortoise.timezone.make_aware(body['last_updated'])
        else:
            body['last_updated'] = tortoise.timezone.make_aware(datetime.datetime.now())

    @staticmethod
    async def update_db_entity_instance(
            model_loc,
            payload: SchemaType,
            db_item: ModelType,
            schem_item: SchemaType,
            service_instance,
            request,
            logged_user_id: uuid.UUID,
    ):
        updated = {}
        for key in model_loc:

            # ID CAN NOT BE UPDATED
            if key in ('unique_id', 'id'):
                continue

            if hasattr(payload, key) and getattr(payload, key) == '__NOT_SET__':
                continue

            if model_loc[key].startswith('cache11.') or model_loc[key].startswith('cache1n.'):

                # if someone want to update field from cache, findout if this field contains id
                # id is only important think, fetch id and update relevant id in model

                attr = getattr(payload, key)
                if isinstance(attr, pydantic.BaseModel):

                    if hasattr(attr, 'id'):
                        attr_model_loc = type(attr).model_loc()['id']

                        target_id = getattr(attr, 'id')
                        if hasattr(db_item, attr_model_loc):
                            if getattr(db_item, attr_model_loc) != target_id:
                                updated[key] = [getattr(db_item, attr_model_loc), target_id]
                                setattr(db_item, attr_model_loc, target_id)

                # all other request will be ignored - for changeing cached item

                continue

            try:
                if not hasattr(payload, key) or not hasattr(schem_item, key):
                    continue

                if getattr(schem_item, key) != getattr(payload, key):
                    old = getattr(schem_item, key)
                    new = getattr(payload, key)

                    if isinstance(new, list):
                        await db_item.fetch_related(key)
                        new_values = []
                        for list_item in new:
                            for old_item in getattr(db_item, key):
                                await old_item.delete()

                            service_loc = service_instance.model.schema_service_loc()
                            new_db_item = await service_loc[key]().create(
                                list_item, request, **list_item.unq(), return_db_object=True
                            )
                            await getattr(db_item, key).add(new_db_item)
                            new_values.append(str(list_item))
                        updated[key] = [old, new_values]
                        continue

                    setattr(db_item, key, new)
                    updated[key] = [old, new]
            except Exception as e:
                raise

        return updated

    @staticmethod
    async def update_updated_fields(
            request: Request,
            model_item: ModelType,
            updated: dict[str, Any],
            schem_item: SchemaType,
            service_instance: Any,
            logged_user_id: uuid.UUID,
    ) -> None:

        if hasattr(schem_item, 'on_change_value'):
            for u in updated.items():
                await getattr(schem_item, 'on_change_value')(
                    key=u[0], new_value=u[1][1], old_value=u[1][0], svc=service_instance, item=model_item,
                    request=request, logged_user_id=logged_user_id
                )

    @staticmethod
    def has_attribute(obj, attr_path):
        attrs = attr_path.split('.')
        for attr in attrs:
            if hasattr(obj, attr):
                obj = getattr(obj, attr)
            else:
                return False
        return True


async def api_accesslog(request, response, session, start_time, accesslog, exc=None):
    # ako se posalje fleg da se ne loguje nemoj da logujes
    if accesslog or request.state > 400:
        payload = {
            'chain': '',
            'uuid': '',
            'method': request.method,
            'path': request.url.path,
            'query_params': request.query_params,
            'path_params': request.path_params,
            'body_params': {},
            'session': session,
            'host': request.client.host,
            'ip': '',
            'x_forwarded_for': '',
            'user_agent': '',
            'total_time': time.time() - start_time,
            'hostname': '',
            'response': response,
            'is_cached': '',
            'status_code': '',
            'requested': datetime.datetime.now().timestamp(),
        }
        if exc:
            payload['exception'] = exc


def api(cache: int = 0, is_authorized: bool = True, accesslog: bool = True,
        headers: Optional[dict] = None, upload_allowed_file_types: Optional[List[str]] = None,
        upload_max_file_size: Optional[int] = None, upload_max_files: Optional[int] = None,
        is_public: bool = True, **route_kwargs):

    if 'path' in route_kwargs:
        route_kwargs['path'] = route_kwargs['path'].rstrip('/')

    def decorator(func: Callable):
        func.route_kwargs = route_kwargs
        func.cache = cache
        func.is_authorized = is_authorized
        func.accesslog = accesslog
        func.headers = headers
        func.upload_allowed_file_types = upload_allowed_file_types
        func.upload_max_file_size = upload_max_file_size
        func.upload_max_files = upload_max_files
        start_time = time.time()

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            self.session = None

            request = kwargs.get("request", None)
            if not request or not isinstance(request, Request):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request object is required")
            request.path_params.update(kwargs)

            # File upload validation
            files = kwargs.get("files", [])
            if not isinstance(files, list):
                files = [files]
            for file in files:
                if upload_allowed_file_types and file.content_type not in upload_allowed_file_types:
                    raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
                if upload_max_file_size and len(await file.read()) > upload_max_file_size:
                    raise HTTPException(status_code=400, detail=f"File size exceeds limit of {upload_max_file_size // (1024 * 1024)} MB")
                if upload_max_files and len(files) > upload_max_files:
                    raise HTTPException(status_code=400, detail=f"Too many files uploaded. Maximum allowed is {upload_max_files}.")

            # Permission check
            if not is_public:
                client_ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
                if client_ip not in ["127.0.0.1", "::1"] and not client_ip.startswith("192.168.") and not client_ip.startswith("172.22."):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "HTTP_403_FORBIDDEN", "ip": client_ip})


            elif is_public:
                token = request.headers.get("Authorization")
                if not is_authorized:
                    self.id_tenant = request.headers.get("X-Tenant-ID")
                # if not self.id_tenant:
                #     raise HTTPException(status_code=401, detail=f"Provide valid X-Tenant-ID")

                elif is_authorized:
                    if token and token.startswith("Bearer "):
                        token = token.replace("Bearer ", "")

                        base_v3 =  request.headers.get("x-base-v3")
                        if base_v3:
                            try:
                                self.session = decode_token_v3(token)
                            except Exception:
                                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                                    detail={"code": "INVALID_SESSION", "parameter": "token", "message": f"error decoding token 1"})
                        else:
                            try:
                                self.session = decode_token(token)
                            except Exception:
                                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                                    detail={"code": "INVALID_SESSION", "parameter": "token", "message": f"error decoding token 1"})

                        if getattr(self.session, 'expired', False):
                            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail={"code": "SESSION_EXPIRED", "parameter": "token", "message": f"your session has expired"})

                        if base_v3:
                            # rdb_session = await self.rdb.get(f"session:{self.session.session_id}")
                            request.me = Me(id=self.session.user_id, role=self.session.role,
                                            id_tenant=self.session.tenant_id, id_session=self.session.session_id)

                        else:
                            rdb_session = await self.rdb.get(f"session:{self.session.session_id}")
                            if not rdb_session:
                                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail={"code": "SESSION_EXPIRED", "parameter": "token", "message": f"your session has expired"})

                            if not isinstance(rdb_session, dict):
                                rdb_session = json.loads(rdb_session)


                            request.me = Me(id=rdb_session['id_user'],
                                            role=rdb_session['role'],
                                            id_tenant=rdb_session['id_tenant'],
                                            id_parent_tenant=rdb_session['id_parent_tenant'],
                                            id_session=rdb_session['session'])

                        if getattr(self.session, 'expired', False):
                            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "SESSION_EXPIRED", "parameter": "token", "message": f"your session has expired"})
                        ...
                        class_path = _get_api_handler_class_path(self)
                        ...
                        func_name = f'{generate_class_aliases(type(self).__name__)}_{func.__name__}'

                        full_api_handler_class_path = f"{class_path}.{func_name}"
                        api_module_name = full_api_handler_class_path.split(".", 2)[1]

                        api_handler = API_HANDLERS.get(api_module_name)
                        if api_handler is None:
                            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"code": "INTERNAL_SERVER_ERROR", "detail": "missing api_handler"})

                        user_role_config = ROLES.get(self.session.role)
                        if user_role_config is None:
                            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail={"code": "HTTP_403_FORBIDDEN"})

                        permissions = user_role_config["permissions"]
                        target_permission_name = f"{api_module_name}.{func_name}"

                        # if rdb_session['permissions']:
                        #     _merge_with_user_permissions(static_permissions=permissions, user_permissions=rdb_session['permissions'])

                        _wildcard_permissions = {}
                        direct_permissions = {}

                        permission = None
                        for perm in permissions:
                            if perm["name"].endswith(".*"):
                                base_name = perm["name"][:-2]  # Remove `.*`
                                _wildcard_permissions[base_name] = perm
                            else:
                                direct_permissions[perm["name"]] = perm

                        if _wildcard_permissions:
                            permission = direct_permissions.get(target_permission_name)
                            if not permission:
                                for base_name, perm in _wildcard_permissions.items():
                                    if target_permission_name.startswith(base_name):
                                        permission = perm
                                        break

                        context = kwargs.get("context", {})

                        if not permission:
                            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "HTTP_403_FORBIDDEN"})

                        if not all(_evaluate_attribute(attr, context, ATTRIBUTES) for attr in permission.get("attributes", [])):
                            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "HTTP_403_FORBIDDEN"})

                        if permission.get("middlewares") and not _apply_middleware(self.session, permission["middlewares"], MIDDLEWARES):
                            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "HTTP_400_BAD_REQUEST"})

                        if permission.get("rate_limit") and is_rate_limited(api_handler, self.session, permission["rate_limit"]):
                            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": "HTTP_429_TOO_MANY_REQUESTS"})

                    else:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"code": "INVALID_SESSION", "parameter": "token", "message": f"error decoding token 2"}
                        )

            # Cache mechanism
            if 'GET' in route_kwargs.get('methods', ['GET']) and cache:
                cache_key = f"cache:{request.method}{self.session.user_id if self.session else ''}{request.url.path}?{request.url.query}"
                try:
                    cached_response = await self.rdb.get(cache_key)
                    if cached_response:
                        return json.loads(cached_response)
                except Exception as e:
                    print(f"Redis cache error: {e}")
                response = await func(self, **request.path_params)
                try:
                    await self.rdb.setex(cache_key, cache, json.dumps(response))
                except Exception as e:
                    print(f"Redis set error: {e}")
                return response

            # Call API handler without cache
            response = await func(self, **request.path_params)
            return response

        return wrapper

    return decorator


def route(router: APIRouter, prefix: str):
    def decorator(cls):
        instance = cls(router)
        router.prefix = prefix
        app.include_router(router, prefix=prefix)
        app.add_middleware(SessionMiddleware, secret_key="d32do34mf234mfl23k4mfl2k34mlf24") # todo, set this from env
        return instance
    return decorator


class BaseAPIHandler(object):

    def __init__(self, router: APIRouter, service=None, model=None, schema=None, table_schema=None):
        self.router = router
        self.service = service
        self.model = model
        self.schema = schema
        self.table_schema = table_schema
        self.rdb = async_redis.get_redis()
        self.register_routes()

    def register_routes(self):
        for attribute_name in dir(self):
            attribute = getattr(self, attribute_name)
            if callable(attribute) and hasattr(attribute, 'route_kwargs'):
                # hack da bi mogao da omogucim da bude method:str u mesto method:list koji je u fast api default
                try:
                    attribute.route_kwargs['methods'] = [attribute.route_kwargs['method']]
                    del attribute.route_kwargs['method']
                except:
                    pass
                route_kwargs = attribute.route_kwargs
                self.router.add_api_route(endpoint=attribute, **route_kwargs)

    @api(
        is_authorized=False,
        method='GET',
        path='/healthy',
    )
    async def healthy(self, request: Request):
        return {'status': 'ok'}


class OptionAPIHandler(object):

    def __init__(self, router: APIRouter, service=None, model=None, schema=None, table_schema=None):
        self.router = router
        self.service = service
        self.model = model
        self.schema = schema
        self.table_schema = table_schema


    @api(
        method='GET',
        path='/options/by-key/{key}',
        response_model=Dict[str, str]
    )
    async def option_get(self, request: Request, key: str) -> dict:
        return await self.service(request).get_option_by_key(key=key)


    @api(
        method='POST',
        path='/options',
    )
    async def option_post(self, data: dict, request: Request) -> dict:
        try:
            validated_data = self.schema(**data)
        except pydantic.ValidationError as e:
            print(e)
            raise HTTPException(status_code=400, detail="Invalid data")

        return await self.service(request).create(
            payload=validated_data,
            request=request,
        )

    @api(
        method='PATCH',
        path='/options/id/{_id}',
    )
    async def option_patch(self, _id: uuid.UUID, data: dict, request: Request) -> dict:
        data = self.schema(**data)
        try:
            res = await self.service(request).update_patch(
                item_id=_id,
                payload=data,
                request=request,
            )
        except Exception as e:
            raise
        return res


class BaseUploadFileHandler(object):

    @api(
        roles=[],
        path='/upload',
        method='POST',
        upload_allowed_file_types=["image/jpeg", "image/png", "image/svg"],
        upload_max_file_size=5 * 1024 * 1024,  # 5 MB
        upload_max_files=5,
    )
    async def upload(self, request: Request, metadata: Optional[str] = Form(None), files: List[UploadFile] = File(...)):

        now = datetime.datetime.now()
        full_upload_dir = f"{str(get_project_root())}/{upload_dir}/{now.year}/{now.month}"
        os.makedirs(full_upload_dir, exist_ok=True)

        if metadata:
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                pass

        response = {}
        for file in files:
            content = await file.read()
            hash_md5 = hashlib.md5()
            hash_md5.update(content)
            with open(
                    f"{full_upload_dir}/{hash_md5.hexdigest()}-{int(time.time())}.{file.filename.split('.')[-1]}", "wb"
            ) as buffer:
                buffer.write(content)
            response[file.filename] = {
                "content_type": file.content_type,
                "size": len(content),
                "description": metadata,
            }
        return response


class BaseWebSocketHandler(object):
    sio_connection = sio_client_manager(write_only=True)

    async def ws_emit(self, event, data={}, room=None):
        await emit(event=event, data=data, room=room, connection=self.sio_connection)


class CRUDAPIHandler(BaseAPIHandler):
    def __init__(self, router, service, schema=None, model=None, table_schema=None):
        self.router = router
        self.service = service
        self.schema = schema
        self.model = model
        self.table_schema = table_schema
        super().__init__(router=router, service=service, model=model, schema=schema, table_schema=table_schema)

    @api(
        method='POST',
        path='',
    )
    async def create(self, data: dict, request: Request, key_id: str = Query(None),) -> dict:
        try:
            validated_data = self.schema(**data)
        except pydantic.ValidationError as e:
            print(e)
            raise HTTPException(status_code=400, detail="Invalid data")

        from fastapi import Response
        response = Response()

        if key_id:
            key_id = key_id.split(',')
            return await self.service(request).create_or_update(key_id, validated_data, request, response)

        try:
            res = await self.service(request).create(
                payload=validated_data,
                request=request,
            )
        except tortoise.exceptions.IntegrityError as e:
            raise HTTPException(status_code=406, detail={"code": "NOT_ACCEPTABLE", "parameter": None, "message": f"Integrity error"})
        except Exception as e:
            raise

        if isinstance(res, tortoise.models.Model):
            return {'id': res.id, 'action': 'created'}

        return res

    @api(
        method='GET',
        path='/id/{_id}',
    )
    async def get_single(self, _id: uuid.UUID, request: Request) -> SchemaType:
        return await self.service(request).get_single(item_id=_id, request=request)

    @api(
        method='GET',
        path='/id/{_id}/fields/{field}',
    )
    async def get_single_field(self, _id: uuid.UUID, field: str,  request: Request) -> Dict:
        return await self.service(request).get_single_field(item_id=_id, field=field, request=request)


    @api(
        method='GET',
        path='',
        response_model=List[Dict] | Dict[str, Any] | UniversalTableResponse
    )
    async def get(self, request: Request, data: UniversalTableGetRequest=Depends()): #-> dict:

        try:
            res = await self.service(request).get_all(request=data, profile_schema=self.table_schema, _request=request)
        except Exception as e:
            raise

        # return res.model_dump(mode='json')
        ...
        return res

    @api(
        method='PUT',
        path='',

    )
    async def update_put(self, data: dict, request: Request) -> dict:
        try:
            validated_data = self.schema(**data)
        except Exception as e:
            raise

        try:
            res = await self.service(request).update_put(
                payload=validated_data,
                request=request,
            )
        except Exception as e:
            raise
        return res

    @api(
        method='DELETE',
        path='/id/{_id}',
    )
    async def delete(self, _id: uuid.UUID, request: Request) -> None:
        return await self.service(request).delete(item_id=_id, request=request)

    @api(
        method='PATCH',
        path='/id/{_id}',
    )
    async def update_patch(self, _id: uuid.UUID, data: dict, request: Request) -> dict:
        data = self.schema(**data)
        try:
            res = await self.service(request).update_patch(
                item_id=_id,
                payload=data,
                request=request,
            )
        except Exception as e:
            raise
        return res
