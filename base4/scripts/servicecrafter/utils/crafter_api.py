from pathlib import Path

from jinja2 import Template

from .templates.api import HEALTHY, INIT, OPTIONS


class CrafterApi:

    @staticmethod
    async def craft(instructions: dict, __init__: Path, healthy: Path, options: Path) -> None:
        name: str = instructions.get('name')

        await CrafterApi.craft_init(__init__=__init__, name=name)
        await CrafterApi.craft_healthy(healthy=healthy, name=name)
        await CrafterApi.craft_options(options=options, name=name)

    @staticmethod
    async def craft_init(__init__: Path, name: str) -> None:
        data: dict = {'app': name}

        template: Template = Template(INIT)
        render: str = template.render(data)

        with open(__init__, 'w') as file:
            file.write(render)

    @staticmethod
    async def craft_healthy(healthy: Path, name: str) -> None:
        data: dict = {'app': name}

        template: Template = Template(HEALTHY)
        render: str = template.render(data)

        with open(healthy, 'w') as file:
            file.write(render)

    @staticmethod
    async def craft_options(options: Path, name: str) -> None:
        data: dict = {'app': name}

        template: Template = Template(OPTIONS)
        render: str = template.render(data)

        with open(options, 'w') as file:
            file.write(render)
