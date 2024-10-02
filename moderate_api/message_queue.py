import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, AsyncIterator, Optional, Union

from aio_pika import connect_robust
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection
from fastapi import Depends
from typing_extensions import Annotated

from moderate_api.config import get_settings
from moderate_api.enums import MessageQueues

_logger = logging.getLogger(__name__)


@dataclass
class Rabbit:
    connection: AbstractRobustConnection
    channel: AbstractRobustChannel


@asynccontextmanager
async def with_rabbit() -> AsyncGenerator[Optional[Rabbit], None]:
    settings = get_settings()

    if not settings.rabbit_router_url:
        _logger.warning("No RabbitMQ URL provided, skipping connection")
        yield None
    else:
        connection = await connect_robust(settings.rabbit_router_url)

        async with connection:
            channel = await connection.channel()
            yield Rabbit(connection=connection, channel=channel)


async def get_rabbit() -> AsyncGenerator[Optional[Rabbit], None]:
    async with with_rabbit() as rabbit:
        yield rabbit


RabbitDep = Annotated[Optional[Rabbit], Depends(get_rabbit)]


async def declare_rabbit_entities(rabbit: Rabbit) -> None:
    _logger.info("Declaring RabbitMQ entities queues and exchanges")

    await rabbit.channel.declare_queue(
        MessageQueues.MATRIX_PROFILE.value, durable=True, auto_delete=False
    )
