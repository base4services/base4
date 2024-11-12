from pathlib import Path

import asyncclick as click

from base4.scripts.servicecrafter.utils import ServiceCrafter

filepath: Path = Path(__file__)


@click.command()
@click.option('-s', '--service_name', help='service name')
async def craft(service_name: str) -> any:
    """Craft a service with instructions in inits"""
    return await ServiceCrafter.craft(service_name)

if __name__ == '__main__':
    craft(_anyio_backend="asyncio")
