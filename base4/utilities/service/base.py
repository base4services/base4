import datetime
import uuid
from typing import Any, Dict, List, TypeVar, Callable
from functools import wraps
import base4.ipc.flow as ipc_flow
import base4.ipc.tenants as ipc_tenants
from fastapi import HTTPException, status, Request
import pydantic
import tortoise
import tortoise.timezone
from base4.schemas.base import NOT_SET
from fastapi import HTTPException, Request
from base4.utilities.security.jwt import decode_token
import jwt

SchemaType = TypeVar('SchemaType', bound=pydantic.BaseModel)
ModelType = TypeVar('ModelType', bound=tortoise.models.Model)



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
                detail={"code": "INTERNAL_SERVER_ERROR", "message": "update_if_exists_key_fields and update_if_exists_value_fields must have same length"},
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
        return await model.gen_unique_id(prefix=uid_prefix, alphabet=uid_alphabet, total_length=uid_total_length, max_attempts=10)

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
                            new_db_item = await service_loc[key]().create(logged_user_id, list_item, request, **list_item.unq(), return_db_object=True)
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
                    key=u[0], new_value=u[1][1], old_value=u[1][0], svc=service_instance, item=model_item, request=request, logged_user_id=logged_user_id
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


def authorization(permission: List[str] = None):
    """
	Autorisation decorator
	"""
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            token = request.headers.get("Authorization")
            if not token or not token.startswith("Bearer "):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_SESSION", "parameter": "token", "message": f"error decoding token"})
            
            token = token.replace("Bearer ", "")
            
            try:
                session = decode_token(token)  # decode_token već treba da postoji
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_SESSION", "parameter": "token", "message": f"error decoding token"})
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_SESSION", "parameter": "token", "message": f"error decoding token"})
            
            if session.expired:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "SESSION_EXPIRED", "parameter": "token", "message": f"your session has been expired"})
            
            # todo, get role from user
            # permission check
            if permission and not any(role in getattr(session, "roles", []) for role in permission):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "FORBIDDEN", "parameter": "token", "message": f"you don't have permission to access this resource"})
            
            return await func(*args, **kwargs, request=request)
        return wrapper
    return decorator
