from pathlib import Path

import aiofiles
import yaml
from jinja2 import Template

from .templates import OPTIONS_MODEL_TEMPLATE, OPTIONS_SCHEMA_TEMPLATE


class CrafterYamls:

    @staticmethod
    async def craft(instructions: dict, models: Path, schemas: Path, table: Path) -> None:
        name: str = instructions.get('name')

        await CrafterYamls.craft_options_model(models=models, name=name)
        await CrafterYamls.craft_options_schema(schemas=schemas, name=name)

    @staticmethod
    async def craft_options_model(models: Path, name: str) -> None:
        data: dict = {'table_name': f'{name}_options', 'app': name}

        template: Template = Template(OPTIONS_MODEL_TEMPLATE)
        render: str = template.render(data)

        content = yaml.safe_load(render)

        with open(models, 'w') as file:
            yaml.dump(content, file, sort_keys=False)

    @staticmethod
    async def craft_options_schema(schemas: Path, name: str) -> None:
        data: dict = dict()

        template: Template = Template(OPTIONS_SCHEMA_TEMPLATE)
        render: str = template.render(data)

        content = yaml.safe_load(render)

        with open(schemas, 'w') as file:
            yaml.dump(content, file, sort_keys=False)
