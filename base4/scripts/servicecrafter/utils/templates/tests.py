test_template = """import os
import pprint
from typing import List

from fastapi import Response 

from .test_base import TestBase

from base4.utilities.files import get_project_root
current_file_path = str(get_project_root())


class {nameCapitalized}FeaturesHelpers(TestBase):
    services = ['{name}', 'tenants']


class Test({nameCapitalized}FeaturesHelpers):

    async def test(self): ...
    
    async def test_options(self):
        KEY, VALUE = ('X', 'Y')

        _response: Response = await self.api('POST', '/api/{name}/options', _body=dict(key=KEY, value=VALUE))
        assert _response.status_code == 201

        _response: Response = await self.api('GET', '/api/{name}/options/by-key/' + KEY)
        assert _response.status_code == 200
        
        json: dict = _response.json()
        assert 'value' in json
        assert json['value'] == VALUE
"""
