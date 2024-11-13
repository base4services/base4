import subprocess
from pathlib import Path

import aiofiles
import yaml

from base4.utilities.files import get_project_root

from .crafter_api import CrafterApi
from .crafter_services import CrafterServices
from .crafter_yamls import CrafterYamls

test_mode: bool = True


class ServiceCrafter:
    _services: Path = Path(get_project_root()) / 'src' / 'services'

    @staticmethod
    async def craft(service_name: str, ) -> bool:
        instructions = {'name': service_name, 'models': [service_name]}
        service: Path = await ServiceCrafter.craft_service(instructions=instructions)
        
        await ServiceCrafter.craft_yaml_sources(instructions=instructions, service=service)
        await ServiceCrafter.craft_schemas(instructions=instructions, service=service)
        await ServiceCrafter.craft_services(instructions=instructions, service=service)
        await ServiceCrafter.craft_models(instructions=instructions, service=service)
        await ServiceCrafter.craft_api(instructions=instructions, service=service)

        await ServiceCrafter.craft_tests(instructions=instructions, service=service)
        config: Path = Path(get_project_root()) / 'config'
        
        await ServiceCrafter.update_configs(name=service_name, config=config)
        await ServiceCrafter.update_services(name=service_name, config=config)
        await ServiceCrafter.update_gen_yaml_and_gen_models(name=service_name)

    @staticmethod
    async def update_gen_yaml_and_gen_models(name: str) -> None:
        root: Path = Path(get_project_root())

        gen_yaml_filepath: Path = root / 'config/gen.yaml'
        # generator: Path = src / 'bin/gen.py'

        content: str = await read_file(filepath=gen_yaml_filepath)
        content: list[str] = content.split('\n')
        new_content: list[str] = list()

        gen: list[str] = [f"  - name: {name}", f"    singular: {name}", f"    location: src/services/{name}", f"    gen:", f"      - models", f"      - schemas"]

        for line in content:
            if line == '  # gen placeholder':
                for item_g in gen:
                    new_content.append(item_g)

                new_content.append('\n')
                new_content.append(line)
                continue

            new_content.append(line)

        new_content: str = '\n'.join(new_content)
        await write_file(filepath=gen_yaml_filepath, content=new_content)

    @staticmethod
    async def update_services(name: str, config: Path) -> None:
        print('s nemanja', config / 'services.yaml')
        
        services_yaml_filepath: Path = config / 'services.yaml'
        if not services_yaml_filepath.exists():
            raise FileNotFoundError('Services yaml not found')

        content: str = await read_file(filepath=services_yaml_filepath)
        content: list[str] = content.split('\n')

        new_content: list[str] = list()

        for line in content:

            if line == '  # services placeholder':
                new_content.append(f'  - {name}:')
                new_content.append(line)
                continue
            new_content.append(line)

        new_content: str = '\n'.join(new_content)

        await write_file(filepath=services_yaml_filepath, content=new_content)

    @staticmethod
    async def craft_service(instructions: dict) -> Path:
        name: str = instructions.get('name')

        service_dir: Path = ServiceCrafter._services / name

        # if service_dir.exists() and test_mode:
        #     import shutil
        #     shutil.rmtree(service_dir)
        
        try:
            service_dir.mkdir()
        except FileExistsError:
            pass

        init_file: Path = service_dir / '__init__.py'
        init_file.touch()

        return service_dir

    @staticmethod
    async def craft_yaml_sources(instructions: dict, service: Path) -> None:
        name: str = instructions.get('name')

        yaml_sources: Path = service / 'yaml_sources'
        try:
            yaml_sources.mkdir()
        except:
            pass

        models: Path = yaml_sources / f'{name}_model.yaml'
        schemas: Path = yaml_sources / f'{name}_schema.yaml'
        table: Path = yaml_sources / f'{name}_table.yaml'

        for file in (
            models,
            schemas,
            table,
        ):
            file.touch()

        await CrafterYamls.craft(instructions=instructions, models=models, schemas=schemas, table=table)

    @staticmethod
    async def craft_services(instructions: dict, service: Path) -> None:
        services: Path = service / 'services'
        services.mkdir()

        _db_conn: Path = services / '_db_conn.py'
        _db_conn.touch()

        options: Path = services / 'options.py'
        options.touch()

        __init__: Path = services / '__init__.py'
        __init__.touch()

        await CrafterServices.craft(instructions=instructions, _db_conn=_db_conn, options=options, __init__=__init__)

    @staticmethod
    async def craft_schemas(instructions: dict, service: Path) -> None:
        name: str = instructions.get('name')
        schemas: Path = service / 'schemas'
        schemas.mkdir()

        __init__: Path = schemas / '__init__.py'
        __init__.touch()

        value: str = f'from .generated_{name}_schema import *\n'
        with open(__init__, 'w') as file:
            file.write(value)

    @staticmethod
    async def craft_models(instructions: dict, service: Path) -> None:
        name: str = instructions.get('name')
        models: Path = service / 'models'
        models.mkdir()

        __init__: Path = models / '__init__.py'
        __init__.touch()

        value: str = f'from .generated_{name}_model import *\n'
        with open(__init__, 'w') as file:
            file.write(value)

    @staticmethod
    async def craft_api(instructions: dict, service: Path) -> None:

        api: Path = service / 'api'
        api.mkdir()

        __init__: Path = api / '__init__.py'
        __init__.touch()

        healthy: Path = api / 'healthy.py'
        healthy.touch()

        options: Path = api / 'options.py'
        options.touch()

        await CrafterApi.craft(instructions=instructions, __init__=__init__, healthy=healthy, options=options)

    @staticmethod
    async def update_configs(config: Path, name: str) -> None:

        db_config: Path = config / 'db.yaml'
        services_config: Path = config / 'services.yaml'

        await ServiceCrafter.register_service_in_db_config(db_config_filepath=db_config, name=name)
        #await ServiceCrafter.register_service_in_environment_files(name=name)
        #await ServiceCrafter.register_service_in_environment_files(name=name, sample=True)

    @staticmethod
    async def register_service_in_environment_files(name: str, sample: bool = False) -> None:
        """Register new service in environment file and sample environment file"""

        filename: str = '.env' if not sample else 'env.sample'
        env_filepath: Path = get_project_root() / filename

        if not env_filepath.exists():
            raise FileNotFoundError(f'Environment file not found in base directory of project!\nFilepath: {str(env_filepath)}')

        env_file_content: str = await read_file(filepath=env_filepath)
        env_file_content: list[str] = env_file_content.split('\n')
        new_env_file_content: list[str] = list()

        for idx, line in enumerate(env_file_content):

            match line.strip():
                case '# DATABASE INFO':
                    new_env_file_content.append(f'DB_{name.upper()}=' + "${DB_NAME_PREFIX}")
                    new_env_file_content.append(line)
                case '# DATABASES LIST':
                    new_env_file_content.append(line)
                    db_list: list[str] = env_file_content[idx + 1]
                    new_db_list: list[str] = db_list[:-1] + f' $DB_{name.upper()})'

                    new_env_file_content.append(new_db_list)

                case '# SERVICES LIST':
                    new_env_file_content.append(line)
                    services_list: list[str] = env_file_content[idx + 1]
                    new_services_list: list[str] = services_list[:-1] + f' "{name}")'

                    new_env_file_content.append(new_services_list)
                    ...
                case _:
                    if 'DATABASES=(' in line or 'SERVICES=(' in line:
                        continue
                    new_env_file_content.append(line)

        new_env_file_content: str = '\n'.join(new_env_file_content)
        await write_file(filepath=env_filepath, content=new_env_file_content)

    @staticmethod
    async def register_service_in_db_config(db_config_filepath: Path, name: str) -> None:
        """Modify db.yaml so new service would be included"""

        db_config_content: str = await read_file(filepath=db_config_filepath)
        db_config_content: list[str] = db_config_content.split('\n')

        new_db_config_content: list = list()

        for idx, line in enumerate(db_config_content):
            match line.strip():
                case '### PLACEHOLDER: APPS':
                    new_db_config_content: list[str] = await ServiceCrafter.include_app(name=name, new_db_config_content=new_db_config_content, idx=idx)
                    new_db_config_content.append(line)
                case '### PLACEHOLDER: CONNECTIONS':
                    new_db_config_content: list[str] = await ServiceCrafter.include_tortoise_connections(name=name, new_db_config_content=new_db_config_content)
                    new_db_config_content.append(line)
                case '### PLACEHOLDER: DB_CONFIG':
                    new_db_config_content: list[str] = await ServiceCrafter.include_db_config(name=name, new_db_config_content=new_db_config_content)
                    new_db_config_content.append(line)
                case _:
                    new_db_config_content.append(line)

        new_db_config_content: str = '\n'.join(new_db_config_content)

        await write_file(filepath=db_config_filepath, content=new_db_config_content)

    @staticmethod
    async def include_app(name: str, new_db_config_content: list[str], idx: int) -> list[str]:

        app: list[str] = [f'    {name}:', f'      models:', f"        - 'services.{name}.models'", f"      default_connection: 'conn_{name}'"]

        for line in app:
            new_db_config_content.append(line)

        return new_db_config_content

    @staticmethod
    async def include_tortoise_connections(name: str, new_db_config_content: list[str]) -> list[str]:
        connection: list[str] = [
            f"    conn_{name}:",
            f"      engine: 'tortoise.backends.asyncpg'",
            f"      credentials: *db_{name}",
        ]

        for line in connection:
            new_db_config_content.append(line)

        return new_db_config_content

    @staticmethod
    async def include_db_config(name: str, new_db_config_content: list[str]) -> list[str]:

        db_config: list[str] = [f"db_{name}: &db_{name}", f"  <<: *db", "  database: ${DB_" + name.upper() + "}"]

        for line in db_config:
            new_db_config_content.append(line)

        return new_db_config_content

    @staticmethod
    async def craft_tests(instructions: dict, service: str) -> None:
        name: str = instructions.get('name')
        if not name:
            raise ValueError('X')

        tests: Path = ServiceCrafter._services.parent.parent / 'tests'
        test_file: Path = tests / f'test_{name}.py'
        test_file.touch()

        from .templates.tests import test_template

        filled_tests = test_template.format(name=name, nameCapitalized=name.capitalize())

        with open(test_file, "w") as file:
            file.write(filled_tests)


async def load_yaml(filepath: Path | str) -> dict:
    """Async load content from yaml file"""

    async with aiofiles.open(filepath, mode='r') as file:
        contents: str = await file.read()
        content: dict = yaml.safe_load(contents)

    return content


async def read_file(filepath: Path | str) -> str:
    """Async read file and returns content"""

    async with aiofiles.open(filepath, mode='r') as file:
        content: str = await file.read()

    return content


async def write_file(filepath: Path | str, content: str) -> None:
    """Async write content in file"""

    async with aiofiles.open(filepath, mode='w') as file:
        await file.write(content)


if __name__ == '__main__':
    filepath: Path = Path(__file__)
    inits: Path = filepath.parent.parent / 'inits'
    sample: Path = inits / 'sample.yaml'

    import asyncio

    asyncio.run(ServiceCrafter.craft(sample))
