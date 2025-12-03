import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from aio_pika import connect_robust
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection
from fastapi import Depends

from moderate_api.config import get_settings
from moderate_api.enums import WorkflowJobTypes

_logger = logging.getLogger(__name__)


@dataclass
class Rabbit:
    connection: AbstractRobustConnection
    channel: AbstractRobustChannel


@asynccontextmanager
async def with_rabbit() -> AsyncGenerator[Rabbit | None, None]:
    settings = get_settings()

    if not settings.rabbit_router_url:
        _logger.warning("No RabbitMQ URL provided, skipping connection")
        yield None
    else:
        connection = await connect_robust(settings.rabbit_router_url)

        async with connection:
            channel = await connection.channel()
            yield Rabbit(connection=connection, channel=channel)  # type: ignore[arg-type]


async def get_rabbit() -> AsyncGenerator[Rabbit | None, None]:
    async with with_rabbit() as rabbit:
        yield rabbit


RabbitDep = Annotated[Rabbit | None, Depends(get_rabbit)]


async def declare_rabbit_entities(rabbit: Rabbit) -> None:
    for queue_type in WorkflowJobTypes:
        _logger.info("Declaring queue %s", queue_type.value)

        await rabbit.channel.declare_queue(
            name=queue_type.value, durable=True, auto_delete=False
        )
