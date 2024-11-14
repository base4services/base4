import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, Request

critical_logger = logging.getLogger("critical_errors")

from enum import Enum, auto
from http import HTTPStatus as status

from base4.utilities.http.methods import HttpMethod

TIMEOUT = 30


class ImpresaApiHandler:
    @staticmethod
    def check_credentials() -> tuple:
        IMPRESA_BASE_URL = os.getenv("IMPRESA_BASE_URL")
        IMPRESA_USERNAME = os.getenv("IMPRESA_USERNAME")
        IMPRESA_PASSWORD = os.getenv("IMPRESA_PASSWORD")
        required_credentials = {"IMPRESA_BASE_URL": IMPRESA_BASE_URL, "IMPRESA_USERNAME": IMPRESA_USERNAME, "IMPRESA_PASSWORD": IMPRESA_PASSWORD}

        missing_credentials: List[str] = [cred for cred, value in required_credentials.items() if value is None]

        if missing_credentials:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "MISSING_REQUIRED_IMPRESA_ENVIRONMENT_VARIABLE(S)",
                    "parameter": "option",
                    "message": f"Missing required environment variable(s): {', '.join(missing_credentials)}",
                },
            )

        return IMPRESA_BASE_URL, IMPRESA_USERNAME, IMPRESA_PASSWORD

    async def make_impresa_request(
        url: str,
        method: HttpMethod = HttpMethod.GET,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> httpx.Response | HTTPException:
        """
        Make an HTTP request using httpx with error handling.

        Args:
            url (str): The URL to make the request to.
            method (str): The HTTP method to use (GET, POST, PUT, DELETE, etc.).
            headers (dict,): A dictionary of HTTP headers to send with the request.
            params (dict, optional): A dictionary of URL parameters to append to the URL.
            data (dict, optional): A dictionary of data to send in the body of the request.
            json (dict, optional): A dictionary of JSON data to send in the body of the request.
            timeout (int): The timeout for the request in seconds.

        Returns:
            httpx.Response: The response from the server.

        Raises:
            httpx.RequestError: If there's a network-related error.
            httpx.HTTPStatusError: If the response has a 4xx or 5xx status code.
            httpx.TimeoutException: If the request times out.
            Exception: For any other unexpected errors.
        """

        (IMPRESA_BASE_URL, IMPRESA_USERNAME, IMPRESA_PASSWORD) = ImpresaApiHandler.check_credentials()

        auth = httpx.BasicAuth(IMPRESA_USERNAME, IMPRESA_PASSWORD)

        url = f"{IMPRESA_BASE_URL}{url}"

        logger = logging.getLogger("__main__")

        logger.info(f"calling api: {url}")
        logger.info(f"request body: {json}")
        logger.info(f"request body data: {data}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(str(method), url, auth=auth, params=params, data=data, json=json, timeout=timeout)
                response.raise_for_status()  # Raises an HTTPStatusError for 4xx and 5xx responses
        except httpx.RequestError as e:
            logger.critical(f"Network-related error occurred after sending a request to impresa: {e}")
            critical_logger.critical(f"Network-related error occurred after sending a request to impresa: {e}")

            raise HTTPException(
                status_code=500, detail={"code": "IMPRESA_NETWORK_ERROR", "parameter": "option", "message": f"Network-related error occurred: {e}"}
            )

        except httpx.HTTPStatusError as e:
            logger.critical(f"HTTP error occurred while sending a request to impresa {url}: {e}")
            critical_logger.critical(f"HTTP error occurred while sending a request to impresa {url}: {e}")

            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "code": "IMPRESA_HTTP_SERVER_ERROR",
                    "parameter": "option",
                    "message": f"error occurred after sending a request to a impresa endpoint {url}, response: {response.text}",
                },
            )

        except httpx.TimeoutException as e:

            raise HTTPException(
                status_code=response.status_code, detail={"code": "HTTP_ERROR_IMPRESA", "parameter": "option", "message": f"Timeout occurred: {e}"}
            )

        except Exception as e:
            logger.critical(f"Unexpected error occurred after sending a request to impresa: {e}")
            critical_logger.critical(f"Unexpected error occurred after sending a request to impresa: {e}")
            raise Exception(f"An unexpected error occurred: {e}")

        logger.info(f"Impresa response status code: {response.status_code}")
        logger.info(f"Impresa response text: {response.text}")
        if 'error' in response.text:
            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "code": "IMPRESA_HTTP_SERVER_ERROR",
                    "parameter": "option",
                    "message": f"error occurred after sending a request to a impresa endpoint {url}, response: {response.text}",
                },
            )

        return response


async def extract_request_body(request: Request) -> Dict[str, Any]:
    # extract request body from fastapi request
    if request.method in ("POST", "PUT", "PATCH"):
        return await request.json()
    else:
        return None
