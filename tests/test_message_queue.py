import logging
import pprint

import aio_pika
import pytest

from moderate_api.enums import WorkflowJobTypes
from moderate_api.message_queue import declare_rabbit_entities, with_rabbit

_SKIP_REASON = "Missing RabbitMQ service"

_logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_broker_publish():
    async with with_rabbit() as rabbit:
        if rabbit is None:
            pytest.skip(_SKIP_REASON)

        await declare_rabbit_entities(rabbit=rabbit)

        await rabbit.channel.default_exchange.publish(
            message=aio_pika.Message(body="Hello Rabbit".encode()),
            routing_key=WorkflowJobTypes.MATRIX_PROFILE.value,
        )


@pytest.mark.asyncio
async def test_broker_ping(client, access_token):
    async with with_rabbit() as rabbit:
        if rabbit is None:
            pytest.skip(_SKIP_REASON)

        for _ in range(3):
            resp = client.get(
                "/ping", headers={"Authorization": f"Bearer {access_token}"}
            )

            resp.raise_for_status()
            resp_json = resp.json()
            _logger.debug("Ping response:\n%s", pprint.pformat(resp_json))
            assert resp_json["broker_connection"]
