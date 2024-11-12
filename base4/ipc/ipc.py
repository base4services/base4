import os
import uuid
from typing import AnyStr, Dict, List, Literal

import httpx
from fastapi.exceptions import HTTPException
from fastapi.requests import Request

from base4.utilities.logging.setup import get_logger

logger = get_logger()


async def ipc(
        handler: Request,
        service: AnyStr,
        method: Literal['GET', 'POST', 'PUT', 'DELETE'],
        uri: AnyStr,
        params: Dict = None,
        body: Dict | List = None,
        return_value_for_key: AnyStr = None,
) -> Dict | str:
    test_mode = os.getenv('TEST_MODE', 'False')
    # base_url = 'TODO'

    url = f'/api/v4/{service}{uri}'

    if test_mode in (True, 'true', 'True'):

        if service not in handler.app.app_services:
            return {}

        from fastapi import FastAPI

        app = handler.app

        timeout = httpx.Timeout(
            connect=30.0,
            read=300.0,
            write=30.0,
            pool=30.0,
        )

        try:
            async with httpx.AsyncClient(app=app, base_url='https://test', timeout=timeout) as client:
                response = await client.request(method, url, params=params, json=body, headers=handler.headers, timeout=timeout)

                if response.status_code not in (200, 201, 204):
                    raise Exception(f"Error: {response.status_code}")

                r = response.json()

                if return_value_for_key:
                    return r[return_value_for_key]

                return r

        except Exception as e:
            raise
    else:
        timeout = httpx.Timeout(
            connect=30.0,
            read=300.0,
            write=30.0,
            pool=30.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:

            if not handler:
                headers = {}
            else:

                # kada radim autorizovane pozive sa mock-om
                # desava se da ostane content-length u headerima
                # od prethodnog poziva, i tu nastaje problem zato
                # ga prisem, sa pretpostavkom da ovo nece napraviti
                # novi problem, testovi ne otkrivaju nista jer se
                # ova grana ne poziva u testovima.

                headers = dict(handler.headers)
                if 'content-length' in headers:
                    del headers['content-length']

            v4installation = os.getenv('V4INSTALLATION', None)
            base_url = 'http://localhost:8000'
            if v4installation == 'docker':
                base_url = f'http://v4_{service}:8000'
            elif v4installation == 'docker-monolith':
                base_url = f'http://v4:8000'

            from base4.ifbreakpoint import ifbreakpoint

            ifbreakpoint()

            try:
                response = await client.request(method, base_url + url, params=params, json=body, headers=headers, timeout=timeout)
                response.raise_for_status()  # raise an HTTPError if the response was unsuccessful
            except httpx.RequestError as e:
                logger.critical(f"Network-related error occurred after sending a request to url {url}: {e}")
                raise HTTPException(
                    status_code=500, detail={"code": "IPC_NETWORK_ERROR", "parameter": "option", "message": f"Network-related error occurred: {e}"}
                )
            except httpx.HTTPStatusError as e:
                logger.critical(f"HTTP error occurred while sending a request to url {url}: {e}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail={
                        "code": "IPC_HTTP_SERVER_ERROR",
                        "parameter": "option",
                        "message": f"error occurred after sending a request to a url endpoint {url}, response: {response.text}",
                    },
                )

            except httpx.TimeoutException as e:
                raise HTTPException(
                    status_code=response.status_code, detail={"code": "HTTP_TIMEOUT_ERROR",
                                                              "parameter": "option",
                                                              "message": f"Timeout occurred: {e}"}
                )

            except Exception as e:
                logger.critical(f"Unexpected error occurred after sending a request to url {url}: {e}")
                raise HTTPException(status_code=500)

            # if response.status_code not in (200, 201, 204):
            #     raise Exception(f"Error: {response.status_code}")

            r = response.json()

            if return_value_for_key:
                return r[return_value_for_key]

            return r

    return f"ipc: raise NotImplementedError test:{test_mode}"


async def get_instance_unique_id(request, instance: str, id_instance: uuid.UUID) -> str:
    instance2service = {'ticket': 'tickets'}
    if instance not in instance2service:
        return "NOT_IMPLEMENTED"
        # raise HTTPException(status_code=400, detail={'code': 'INVALID_INSTANCE', 'message': instance})

    try:
        res = await ipc(request, instance2service[instance], 'GET', f'/{id_instance}/unique_id', return_value_for_key='value')

        ...
    except Exception as e:
        raise

    return res
