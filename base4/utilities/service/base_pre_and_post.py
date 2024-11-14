import inspect
from typing import Any, Dict, TypeVar

import tortoise.models
from fastapi import HTTPException, Request
from pydash import sample

SchemaType = TypeVar('SchemaType')
ModelType = TypeVar('ModelType', bound=tortoise.models.Model)


class BaseServicePreAndPostUtils:
    @staticmethod
    async def create_pre_save_hook(payload: SchemaType, service_instance: Any, request: Request, body: Dict[str, Any]) -> None:
        """
        Execute the pre-save hook for create operation if it exists on the payload.

        This method checks if the payload has a 'pre_save_create' method and executes it
        if present. It handles exceptions and raises appropriate HTTP exceptions if the
        hook fails or encounters an error.

        Args:
            payload (SchemaType): The payload object that may contain a 'pre_save_create' method.
            service_instance (Any): The service instance to be passed to the pre-save hook.
            request (Request): The FastAPI request object.
            body (Dict[str, Any]): The dictionary containing the data to be saved.

        Raises:
            HTTPException: If the pre-save hook fails or encounters an error.

        Returns:
            None

        Note:
            The 'pre_save_create' method, if it exists, should be an asynchronous method
            that takes the following parameters: svc, db_id, request, body, and payload.
        """
        if hasattr(payload, 'pre_save_create') and inspect.ismethod(getattr(payload, 'pre_save_create')):
            try:
                psc_res = await getattr(payload, 'pre_save_create')(svc=service_instance, db_id=body['id'], request=request, body=body, payload=payload)
                if not psc_res:
                    raise HTTPException(
                        status_code=400,
                        detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "pre_save_create", "message": "pre_save_create method failed"},
                    )

            except HTTPException as e:
                raise e
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "pre_save_create", "message": f"Error in pre_save_create method: {str(e)}"},
                )

    @staticmethod
    async def create_post_save_hook(payload: SchemaType, service_instance: Any, request: Request, item: ModelType) -> Dict[str, Any]:
        """
        Execute the post-save hook for create operation if it exists on the payload.

        This method checks if the payload has a 'post_commit' method and executes it
        if present. It handles exceptions and raises appropriate HTTP exceptions if the
        hook fails or encounters an error.

        Args:
            payload (SchemaType): The payload object that may contain a 'post_commit' method.
            service_instance (Any): The service instance to be passed to the post-save hook.
            request (Request): The FastAPI request object.
            item (ItemType): The item that was just created and saved.

        Raises:
            HTTPException: If the post-save hook fails or encounters an error.

        Returns:
            Dict[str, Any]: The result of the post_commit method, or an empty dict if the method doesn't exist.

        Note:
            The 'post_commit' method, if it exists, should be an asynchronous method
            that takes the following parameters: svc, item, and request.
            If the post_commit method fails, the newly added entry should be deleted,
            but this deletion is not implemented in this method (see TODO comments).
        """
        post_commit_result: Dict[str, Any] = {}
        if hasattr(payload, 'post_commit') and inspect.ismethod(getattr(payload, 'post_commit')):
            try:
                post_commit_result = await getattr(payload, 'post_commit')(svc=service_instance, item=item, request=request)
                if post_commit_result is False:
                    # TODO: Delete the newly added entry

                    raise HTTPException(
                        status_code=500, detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_commit", "message": "post_commit method failed"}
                    )

            except Exception as e:
                # TODO: Delete the newly added entry

                raise HTTPException(
                    status_code=500, detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_commit", "message": f"Error in post_commit method: {str(e)}"}
                )
        return post_commit_result

    @staticmethod
    async def update_pre_save_hook(payload: SchemaType, service_instance: Any, request: Request, item: ModelType) -> None:
        """
        Execute the pre-save update hook if it exists on the payload.

        This method checks if the payload has a 'pre_save_update' method and executes it.
        If the method execution fails or returns False, it raises an HTTPException.

        Args:
            payload (SchemaType): The payload object that may contain the pre_save_update method.
            service_instance (Any): The service instance to be passed to the pre_save_update method.
            request (Request): The FastAPI request object.
            item (ModelType): The database item being updated.

        Raises:
            HTTPException: If the pre_save_update method fails or returns False, or if any other exception occurs.

        Returns:
            None
        """
        if hasattr(payload, 'pre_save_update') and inspect.ismethod(getattr(payload, 'pre_save_update')):
            try:
                pre_save_update_method = getattr(payload, 'pre_save_update')
                if not await pre_save_update_method(svc=service_instance, db_id=item.id, request=request, body=None, payload=payload):
                    raise HTTPException(
                        status_code=400, detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "pre_save_update", "message": "pre_save method failed"}
                    )
            except HTTPException as e:
                raise e
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "pre_save_update", "message": f"Error in pre_save_update method: {str(e)}"},
                )

    @staticmethod
    async def update_post_save_hook(payload: SchemaType, service_instance: Any, request: Request, item: ModelType, updated: Dict[str, Any]) -> dict | None:
        """
        Execute the post-save update hook if it exists on the payload.

        This method checks if the payload has a 'post_commit_update' method and executes it.
        If the method execution returns False, it raises an HTTPException.

        Args:
            payload (SchemaType): The payload object that may contain the post_commit_update method.
            service_instance (Any): The service instance to be passed to the post_commit_update method.
            request (Request): The FastAPI request object.
            item (ModelType): The database item being updated.
            updated (Dict[str, Any]): A dictionary containing the updated fields.

        Raises:
            HTTPException: If the post_commit_update method returns False or if any other exception occurs.

        Returns:
            Optional[Dict[str, Any]]: The result of the post_commit_update method, if any.
        """
        if hasattr(payload, 'post_commit_update') and inspect.ismethod(getattr(payload, 'post_commit_update')):
            try:
                post_commit_update_method = getattr(payload, 'post_commit_update')
                post_commit_update_result = await post_commit_update_method(svc=service_instance, item=item, updated=updated, request=request)
                if post_commit_update_result is False:
                    raise HTTPException(
                        status_code=400,
                        detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_commit_update", "message": "post_commit_update method failed"},
                    )
            except HTTPException as e:
                raise e
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INTERNAL_SERVER_ERROR", "parameter": "post_commit_update", "message": f"Error in post_commit_update method: {str(e)}"},
                )
            return post_commit_update_result
