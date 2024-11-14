import importlib
import uuid
from typing import Any, Dict, List, Optional, Type, TypeVar, cast

import pydantic
import tortoise.exceptions
import tortoise.models
from fastapi import APIRouter, Depends, FastAPI, Query, Response, status
from fastapi.exceptions import HTTPException
from fastapi.requests import Request

from base4.schemas.universal_table import UniversalTableGetRequest, UniversalTableResponse

# from base4.schemas.crud import CreateItemParamsRequest
from base4.service.base import BaseService
from base4.utilities.security.jwt import DecodedToken, verify_token

BaseServiceClassType = TypeVar("BaseServiceClassType", bound=BaseService)


def create_endpoints(
    router: APIRouter,
    endpoints: Dict[str, Dict[str, Type]],
    service_name: str,
    singular_object_name: str,
    plural_object_name: str,
    default_table_profile: str = 'default',
    functions: set = None,
    verify_token_method: Any = verify_token,
    verify_token_per_method: Optional[Dict[str, Any]] = None,
):
    for path, config in endpoints.items():
        service_class: Type[BaseService] = cast(Type[BaseService], config['service'])
        schema_class = config['schema']

        if not functions or 'get_single' in functions:

            try:
                the_verify_token_method = verify_token_per_method.get('get_single', verify_token_method) if verify_token_per_method else verify_token_method
            except Exception as e:
                raise

            @router.get(path + '/{_id}', response_model=schema_class)
            async def get_single(
                _id: uuid.UUID,
                request: Request,
                service_class=service_class,
                schema_class=schema_class,
                _session: DecodedToken = Depends(the_verify_token_method),
            ):
                service = service_class()
                res = await service.get_single(_id, request)
                return res

        if not functions or 'get_single_field' in functions:
            the_verify_token_method = verify_token_per_method.get('get_single_field', verify_token_method) if verify_token_per_method else verify_token_method

            @router.get(path + '/{_id}/{field}', response_model=Any)
            async def get_single_field(
                _id: uuid.UUID, field: str, request: Request, service_class=service_class, _session: DecodedToken = Depends(the_verify_token_method)
            ):
                service = service_class()
                res = await service.get_single_field(_id, field, request)
                return res

        if not functions or 'create' in functions:

            the_verify_token_method = verify_token_per_method.get('create', verify_token_method) if verify_token_per_method else verify_token_method

            @router.post(path)
            async def create(
                payload: schema_class,
                request: Request,
                response: Response,
                key_id: str = Query(None),
                _session: DecodedToken = Depends(the_verify_token_method),
            ) -> Any:
                try:
                    service: service_class = service_class()
                except Exception as e:
                    raise

                # logged_user_id = uuid.UUID('00000000-0000-0000-0000-000000000000')

                if key_id:
                    key_id = key_id.split(',')
                    return await service.create_or_update(_session.user_id, key_id, payload, request, response)

                # print('/' * 100)
                # print(payload)
                # print('/' * 100)

                try:
                    res = await service.create(_session.user_id, payload, request)
                except tortoise.exceptions.IntegrityError as e:
                    raise HTTPException(status_code=406, detail={"code": "NOT_ACCEPTABLE", "parameter": None, "message": f"Integrity error"})
                except Exception as e:
                    raise

                response.status_code = 201
                # res = res.model_dump()
                # if 'action' not in res:
                #     res['action'] = 'created'
                #
                # return res
                if isinstance(res, tortoise.models.Model):
                    return {'id': res.id, 'action': 'created'}

                return res

            @router.patch(path + '/{item_id}/validate')
            async def validate(item_id: uuid.UUID, _request: Request, _session: DecodedToken = Depends(the_verify_token_method)) -> Dict:

                service: service_class = service_class()

                return await service.validate(_session.user_id, item_id=item_id, request=_request)

        if not functions or 'get' in functions:

            the_verify_token_method = verify_token_per_method.get('get', verify_token_method) if verify_token_per_method else verify_token_method

            @router.get(path, response_model=List[Dict] | Dict[str, Any] | UniversalTableResponse)
            async def get(request: Request, params: UniversalTableGetRequest = Depends(), _session: DecodedToken = Depends(the_verify_token_method)) -> Any:
                service: service_class = service_class()

                if params.profile:
                    profile = params.profile.capitalize()
                else:
                    profile = default_table_profile  # TODO: Use from params

                sch = f'profiles.{service_name.capitalize()}{profile.capitalize()}Schema'

                # DO NOT REMOVE THIS LINE - eval(sch) uses it

                # modul = f'services.{service_name}.schemas.generated_{singular_object_name}_table'

                modul = f'services.{service_name}.schemas'

                profiles = importlib.import_module(modul)

                try:
                    res = await service.get_all(params, eval(sch), _request=request)
                    ...
                except Exception as e:
                    raise

                return res

        if not functions or 'update' in functions:
            the_verify_token_method = verify_token_per_method.get('update', verify_token_method) if verify_token_per_method else verify_token_method

            @router.patch(path + '/{_id}', response_model=Dict[str, Any])
            async def update(_id: uuid.UUID, payload: schema_class, request: Request, _session: DecodedToken = Depends(the_verify_token_method)) -> Any:
                service = service_class()
                # logged_user_id = uuid.UUID('00000000-0000-0000-0000-000000000000')

                updated = await service.update(_session.user_id, _id, payload, request)
                return updated

        if not functions or 'delete' in functions:
            the_verify_token_method = verify_token_per_method.get('delete', verify_token_method) if verify_token_per_method else verify_token_method

            @router.delete(path + '/{_id}', response_model=Dict[str, Any])
            async def delete(_id: uuid.UUID, request: Request, _session: DecodedToken = Depends(the_verify_token_method)) -> Dict:
                service = service_class()
                # logged_user_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
                await service.delete(_session.user_id, _id, request)
                return {'deleted': _id}
