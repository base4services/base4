import inspect
import asyncio
import logging
import os
import sys
from functools import wraps
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Type

import tortoise
from fastapi import HTTPException, status

from base4 import configuration

import contextlib
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import yaml
import base4.utilities.files as paths
import logging.config
import json

def log_json_to_pipe(d, parent_key=''):

    def lj2p(d, parent_key):

        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(lj2p(v, new_key))
            else:
                items.append(f"{new_key}={v}")

        return items if parent_key else "|".join(items)


    if isinstance(d, dict):
        
        a = lj2p(d, parent_key)
        return a
 
    return str(d)       
        
#    # expecting dict, but sometimes string can be sent
#    if  isinstance(d, str):
#        try:
#            # if this string is valid json, convert it to dict and log as dict
#            d=json.loads(d)
#            return lj2p(d, parent_key)
#        except Exception as e:
#            
#            # othervise just log as given string
#            return d
#    return lj2p(d, parent_key)


@contextlib.contextmanager
def temporary_console_logging(service):
    logger = logging.getLogger(service)

    handler = logging.StreamHandler()
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)

def get_parent_logger():
    # Get the caller's module (the module that imported common.py)
    frame = inspect.currentframe().f_back
    calling_module = inspect.getmodule(frame)
    
    if calling_module:
        # Get the logger from the caller's namespace
        for name, logger in calling_module.__dict__.items():
            if isinstance(logger, logging.Logger):
                return logger
    
    # Fallback to root logger if no logger found in parent module
    return logging.getLogger()
    

def setup_logging():
    config_path: str = paths.config() / 'logging.yaml'

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize logging config
    logging.config.dictConfig(config['logging'])


def log_debug_json(log, anchor, data, isolate=True):

    if isolate:
        log.debug('\n'*5)
        log.debug('-'*80)

    log.debug(f"ANCHOR: {anchor}")
    log.debug('\n'+json.dumps(data, indent=4, ensure_ascii=False,default=str))

    if isolate:
        log.debug('-'*80)
        log.debug('\n'*5)



# def setup_logging() -> None:
#     """
#     Set up logging for each d_service defined in the configuration.
#     It reads the logging level from the environment variable LOGGING_LEVEL
#     and sets up rotating file and stream handlers for each d_service's logger.
#     """
#     logging_level = os.environ.get('LOGGING_LEVEL', 'INFO').upper()
#     numeric_level = getattr(logging, logging_level, None)
#     if not isinstance(numeric_level, int):
#         raise ValueError(f'Invalid log level: {logging_level}')
#
#     services = [svc for svc in configuration("services")["services"]]
#     print('servicesservices', services)
#     # services.append("impresaone2")    # REMOVED
#
#     for service in services:
#         logger = logging.getLogger(service)
#         logger.setLevel(numeric_level)
#
#         # Set up RotatingFileHandler
#         # TODO: USE THIS FROM ENV_CONFIG
#         log_file_path = f"/tmp/base4project/{service}.log"
#
#         # First ensure the directory exists
#         os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
#
#         # Then check if file exists, if not create it
#         if not os.path.exists(log_file_path):
#             # Create empty file
#             open(log_file_path, 'w').close()
#
#         rotating_file_handler = RotatingFileHandler(log_file_path, maxBytes=10 * 1024 * 1024, backupCount=1)  # 10 MB
#         formatter = logging.Formatter("%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
#         rotating_file_handler.setFormatter(formatter)
#
#         # Set up StreamHandler
#         stream_handler = logging.StreamHandler()
#         stream_handler.setFormatter(formatter)
#
#         # Clear existing handlers and add new ones
#         logger.handlers.clear()
#         logger.addHandler(rotating_file_handler)
#         logger.addHandler(stream_handler)
#
#         # Prevent propagation to root logger
#         logger.propagate = False


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
        logger = "base4project"
    return logging.getLogger(logger)


def print_logging_config():

    import pprint
    # Get root logger
    root = logging.getLogger()

    # Print basic info about root logger
    print(f"Root logger level: {logging.getLevelName(root.level)}")

    # Print handlers information
    print("\nHandlers:")
    for i, handler in enumerate(root.handlers):
        print(f"\nHandler {i + 1}:")
        print(f"  Type: {type(handler).__name__}")
        print(f"  Level: {logging.getLevelName(handler.level)}")

        # If it's a file handler, print the filename
        if hasattr(handler, 'baseFilename'):
            print(f"  File: {handler.baseFilename}")

        # Print formatter details
        if handler.formatter:
            print(f"  Format: {handler.formatter._fmt}")
            print(f"  DateFormat: {handler.formatter.datefmt}")

    # Print effective logging config if available
    try:
        print("\nLogging config dictionary:")
        config_dict = logging.Logger.manager.loggerDict
        pprint.pprint(config_dict)
    except:
        print("Could not retrieve logging config dictionary")




def inspect_logging_config():
    # Get all configured loggers
    loggers = [logging.getLogger()]  # Start with root logger
    loggers.extend([logging.getLogger(name) for name in logging.Logger.manager.loggerDict])

    for logger in loggers:
        print(f"\n{'=' * 50}")
        print(f"LOGGER: {logger.name if logger.name else 'root'}")
        print(f"Level: {logging.getLevelName(logger.level)}")
        print(f"Propagate: {logger.propagate}")
        print(f"Disabled: {logger.disabled}")

        if not logger.handlers and logger.propagate:
            print("No handlers directly attached. Uses parent handlers.")

        for i, handler in enumerate(logger.handlers):
            print(f"\n  HANDLER {i + 1}: {type(handler).__name__}")
            print(f"  Level: {logging.getLevelName(handler.level)}")

            # File handler details
            if isinstance(handler, logging.FileHandler):
                print(f"  Target: FILE")
                print(f"  Path: {handler.baseFilename}")
                print(f"  Mode: {handler.mode}")
                print(f"  Encoding: {handler.encoding}")

                if isinstance(handler, RotatingFileHandler):
                    print(f"  Max Bytes: {handler.maxBytes}")
                    print(f"  Backup Count: {handler.backupCount}")

                if isinstance(handler, TimedRotatingFileHandler):
                    print(f"  Rotation: {handler.when}")
                    print(f"  Interval: {handler.interval}")

            # Stream handler details
            elif isinstance(handler, logging.StreamHandler):
                import sys
                stream_name = "stderr" if handler.stream == sys.stderr else "stdout" if handler.stream == sys.stdout else "custom stream"
                print(f"  Target: STREAM ({stream_name})")

            # Try to detect Redis handlers (common pattern in 3rd party handlers)
            elif 'redis' in type(handler).__name__.lower():
                print(f"  Target: REDIS (detected from class name)")
                # Try to extract connection info if available
                for attr in ['host', 'port', 'db', 'key', 'channel']:
                    if hasattr(handler, attr):
                        print(f"  Redis {attr}: {getattr(handler, attr)}")

            else:
                print(f"  Target: OTHER")

            # Formatter details
            if handler.formatter:
                print(f"  Format: {handler.formatter._fmt}")
                print(f"  DateFormat: {handler.formatter.datefmt or 'default'}")


if __name__ == "__main__":
    setup_logging()
