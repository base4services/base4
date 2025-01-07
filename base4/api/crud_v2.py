import uuid
from typing import List, Dict
from base4.utilities.service.base import BaseAPIHandler, api, route
from fastapi import APIRouter, Request



class CRUDAPIHandler(object):
	def __init__(self, router):
		self.service = 'example service module path'
		self.schema = 'example service schema path'
		self.model = 'example service model path'
		super().__init__(router)

	@api(
		method='GET',
		path='/id/{_id}',
		# response_model = Dict[str, str],
		# cache: int = 0,
		# is_accesslog: bool = True,
		# upload_allowed_file_types: Optional[List[str]] = None,
		# upload_max_file_size: Optional[int] = None,
		# upload_max_files: Optional[int] = None
		# is_authorized: bool = False,
		# is_public=False,
	)
	async def get_single(self, request: Request) -> dict:
		return {"hello": "world"}

	@api(
		method='GET',
		path='/id/{_id}/{field}',

	)
	async def get_single_field(self, request: Request) -> dict:
		return {"hello": "world"}

	@api(
		method='POST',
		path='/',

	)
	async def create(self, request: Request) -> dict:
		return {"hello": "world"}

	@api(
		method='POST',
		path='/id/{item_id}/validate',

	)
	async def validate(self, request: Request) -> dict:
		return {"hello": "world"}

	@api(
		method='GET',
		path='/',
		response_model=List[Dict] | Dict[str, Any] | UniversalTableResponse
	)
	async def get(self, request: Request) -> dict:
		return {"hello": "world"}

	@api(
		method='PATCH',
		path='/id/{_id}',
		response_model=Dict[str, Any]
	)
	async def update_by_id(self, request: Request) -> dict:
		return {"hello": "world"}

	@api(
		method='DELETE',
		path='/id/{_id}',
		response_model=Dict[str, Any]
	)
	async def delete_by_id(self, request: Request) -> dict:
		return {"hello": "world"}


# def mk_crud_api_handler(api_router: APIRouter, api_prefix: str,
#                         implements=None, ):
#     if not implements:
#         implements = ['create','read','update','patch','delete','list']
#
#     cls_name = 'CRUDClass'
#
#     @route(router=api_router, prefix=f'/api/{api_prefix.strip("/")}')
#     class CRUDClass(BaseAPIHandler):
#
#         prefix = api_prefix.strip("/")
#
#         def __init__(self, r):
#             # self.service = service
#             # self.schema = schema
#             # self.model = model
#             super().__init__(r)
#
#
#         if 'read' in implements:
#             @api(
#                 method='GET',
#                 path='/id/{_id}',
#             )
#             async def get_single(self, _id: uuid.UUID, request: Request) -> dict:
#                 return {"TBD": "GET"}
#
#         if 'list' in implements:
#             @api(
#                 method='GET',
#                 path='',
#             )
#             async def list_all(self, _id: uuid.UUID, request: Request) -> dict:
#                 return {"TBD": "LIST"}
#
#         if 'create' in implements:
#             @api(
#                 # is_authorized=False,
#                 method='POST',
#                 path='',
#             )
#             async def create(self, request: Request) -> dict:
#
#                 return {"TBD": "CREATE"}
#
#         if 'update' in implements:
#             @api(
#                 method='PUT',
#                 path='/id/{_id}',
#             )
#             async def update(self, _id: uuid.UUID, request: Request) -> dict:
#                 return {"TBD": "UPDATE(PUT)"}
#
#         if 'patch' in implements:
#             @api(
#                 method='PATCH',
#                 path='/id/{_id}',
#             )
#             async def patch(self, _id: uuid.UUID, request: Request) -> dict:
#                 return {"TBD": "UPDATE(PATCH)"}
#
#         if 'delete' in implements:
#             @api(
#                 method='DELETE',
#                 path='/id/{_id}',
#             )
#             async def delete(self, _id: uuid.UUID, request: Request) -> dict:
#                 return {"TBD": "DELETE"}
#
#     return CRUDClass
#
#     # name = f"{cls_name}_{api_prefix.strip('/').replace('/', '_')}"
#     #
#     # return  type(name, (CRUDClass,), {}, metaclass=CRUDClass.__class__)
#     # pera.append( type(name, (CRUDClass,), {}) )
#     # new_class = type(f"OPETISTO", CRUDClass.__bases__, dict(CRUDClass.__dict__))
#     #
#     # pera.append(new_class)
#     # return pera[-1]