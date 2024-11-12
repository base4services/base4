INIT = """from fastapi import APIRouter

router = APIRouter()
from base4.utilities.service.startup import service as app
from .healthy import *
from .options import *
app.include_router(router, prefix="/api/{{ app }}")

"""


HEALTHY = """from . import router


@router.get('/healthy')
async def healthy():
    return {'status': 'healthy', 'service': '{{ app }}'}

"""


OPTIONS = """from typing import Dict

from fastapi import Depends

import services.{{ app }}.schemas as schemas
import services.{{ app }}.services as services
from base4.api.crud import create_endpoints
from base4.utilities.security.jwt import DecodedToken, verify_token

from . import router


@router.get('/options/by-key/{key}', response_model=Dict[str, str])
async def get_option_by_key(key: str, _session: DecodedToken = Depends(verify_token)):
    service = services.OptionService()
    return await service.get_option_by_key(key)


endpoints_config = {
    '/options': {
        'service': services.OptionService,
        'schema': schemas.OptionSchema,
    },
}

create_endpoints(
    router, endpoints_config, service_name='{{ app }}', singular_object_name='{{ app }}', plural_object_name='{{ app }}', functions={'get_single', 'create', 'update'}
)
"""
