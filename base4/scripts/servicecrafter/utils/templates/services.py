_DB_CONN = """import os


def get_conn_name():
    if os.environ.get('TEST_MODE', None) in ('true', 'True', 'TRUE', '1'):
        return 'conn_test'

    return 'conn_{{ app }}'
"""

OPTIONS_SERVICE = """import logging
from typing import Dict

from fastapi.exceptions import HTTPException

import services.{{ app }}.models as models
import services.{{ app }}.schemas as schemas
from base4.utilities.logging.setup import class_exception_traceback_logging, get_logger
from base4.service.base import BaseService

from ._db_conn import get_conn_name

logger = get_logger()


@class_exception_traceback_logging(logger)
class OptionService(BaseService[models.Option]):

    def __init__(self):
        super().__init__(schemas.OptionSchema, models.Option, get_conn_name())

    async def get_option_by_key(self, key: str) -> Dict[str, str]:
        res = await models.Option.filter(key=key).get_or_none()

        if not res:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "parameter": "option", "message": f"option for key {key} not found"})

        return {'id': str(res.id), 'value': res.value}
"""
