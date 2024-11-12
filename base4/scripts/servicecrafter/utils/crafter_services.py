from pathlib import Path

from jinja2 import Template

from .templates.services import _DB_CONN, OPTIONS_SERVICE


class CrafterServices:

    @staticmethod
    async def craft(instructions: dict, _db_conn: Path, options: Path, __init__: Path) -> None:
        name: str = instructions.get('name')

        await CrafterServices.craft_db_conn(_db_conn=_db_conn, name=name)
        await CrafterServices.craft_options_service(options=options, name=name)
        await CrafterServices.craft_init(__init__=__init__)

    @staticmethod
    async def craft_db_conn(_db_conn: Path, name: str) -> None:
        data: dict = {'app': name}

        template: Template = Template(_DB_CONN)
        render: str = template.render(data)

        with open(_db_conn, 'w') as file:
            file.write(render)

    @staticmethod
    async def craft_options_service(options: Path, name: str) -> None:
        data: dict = {'app': name}

        template: Template = Template(OPTIONS_SERVICE)
        render: str = template.render(data)

        with open(options, 'w') as file:
            file.write(render)

    @staticmethod
    async def craft_init(__init__: Path) -> None:

        value: str = 'from .options import *\n'
        with open(__init__, 'w') as file:
            file.write(value)
