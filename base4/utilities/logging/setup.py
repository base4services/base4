import asyncio
import logging
import os
import sys
from functools import wraps
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Type

import tortoise
from base4 import configuration
from fastapi import HTTPException, status


def setup_logging() -> None:
    """
    Set up logging for each d_service defined in the configuration.
    It reads the logging level from the environment variable LOGGING_LEVEL
    and sets up rotating file and stream handlers for each d_service's logger.
    """
    logging_level = os.environ.get('LOGGING_LEVEL', 'INFO').upper()
    numeric_level = getattr(logging, logging_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {logging_level}')

    services = [list(svc.keys())[0] for svc in configuration("services")["services"]]
    print('servicesservices', services)
    # services.append("impresaone2")    # REMOVED

    for service in services:
        logger = logging.getLogger(service)
        logger.setLevel(numeric_level)

        # Set up RotatingFileHandler
        # TODO: USE THIS FROM ENV_CONFIG
        log_file_path = f"/tmp/base4project/{service}.log"

        # First ensure the directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        # Then check if file exists, if not create it
        if not os.path.exists(log_file_path):
            # Create empty file
            open(log_file_path, 'w').close()

        rotating_file_handler = RotatingFileHandler(log_file_path, maxBytes=10 * 1024 * 1024, backupCount=1)  # 10 MB
        formatter = logging.Formatter("%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        rotating_file_handler.setFormatter(formatter)

        # Set up StreamHandler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        # Clear existing handlers and add new ones
        logger.handlers.clear()
        logger.addHandler(rotating_file_handler)
        logger.addHandler(stream_handler)

        # Prevent propagation to root logger
        logger.propagate = False


def exception_traceback_logging(logger: logging.Logger) -> Callable:
    """
    Decorator for logging exceptions in asynchronous functions.

    Args:
        logger (logging.Logger): The logger to use for logging exceptions.

    Returns:
        Callable: A decorator that can be applied to asynchronous functions.
    """

    def decorator(funct: Callable) -> Callable:
        @wraps(funct)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                logger.debug(f"calling method {funct.__name__}")
                logger.debug(f"function {funct.__name__} positional arguments {args}")
                logger.debug(f"function {funct.__name__} keyword arguments {kwargs}")
                return await funct(*args, **kwargs)
            except HTTPException as http_exc:
                logger.exception(f"An exception occurred in {funct.__name__}: {http_exc}")
                # Re-raise the original HTTPException
                raise http_exc
            except tortoise.exceptions.IntegrityError as e:
                raise HTTPException(status_code=406, detail={"code": "NOT_ACCEPTABLE", "parameter": None, "message": f"Integrity error"})

            except Exception as e:
                # Log the exception and raise a 500 Internal Server Error
                logger.exception(f"An exception occurred in {funct.__name__}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return wrapper

    return decorator


def class_exception_traceback_logging(logger: logging.Logger) -> Callable:
    """
    Class decorator for applying exception_traceback_logging to all async methods of a class.

    Args:
        logger (logging.Logger): The logger to use for logging exceptions.

    Returns:
        Callable: A class decorator.
    """

    def class_decorator(cls: Type) -> Type:
        for name, method in cls.__dict__.items():
            if callable(method) and asyncio.iscoroutinefunction(method):
                setattr(cls, name, exception_traceback_logging(logger)(method))
        return cls

    return class_decorator


def get_logger():
    """
    Get a logger instance for a specific service or monolith application.

    """
    if len(sys.argv) > 1 and sys.argv[1]:
        logger = sys.argv[1]
    else:
        logger = "base4project" # "impresaone2"
    return logging.getLogger(logger)


if __name__ == "__main__":
    setup_logging()
