import asyncio
import json
import logging
import pprint
import random
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from moderate_api.db import with_session
from moderate_api.entities.asset.models import Asset, UploadedS3Object
from moderate_api.entities.job.models import WorkflowJob
from moderate_api.enums import WorkflowJobTypes
from moderate_api.main import app
from moderate_api.message_queue import Rabbit, with_rabbit
from tests.utils import upload_test_files

_DEFAULT_MESSAGE_TIMEOUT_SECS = 10

_logger = logging.getLogger(__name__)


async def _wait_for_matrix_profile_message(
    rabbit: Rabbit, analysis_variable: str
) -> None:
    queue = await rabbit.channel.declare_queue(
        WorkflowJobTypes.MATRIX_PROFILE.value, durable=True
    )

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    msg_data = json.loads(message.body.decode())
                except json.JSONDecodeError:
                    continue

                _logger.info("Received message:\n%s", pprint.pformat(msg_data))

                if msg_data.get("analysis_variable") == analysis_variable:
                    break


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "access_token",
    [{"is_admin": True}],
    indirect=True,
)
async def test_matrix_profile_workflow_job(access_token):  # type: ignore[no-untyped-def]
    async with with_rabbit() as rabbit:
        if rabbit is None:
            pytest.skip()

    asset_id = upload_test_files(access_token, num_files=random.randint(1, 4))

    async with with_session() as session:
        result = await session.execute(
            select(UploadedS3Object).where(Asset.id == asset_id)
        )

        s3_object = result.scalars().first()

    analysis_variable = uuid.uuid4().hex

    with TestClient(app) as client:
        resp_job = client.post(
            "/job",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "job_type": WorkflowJobTypes.MATRIX_PROFILE.value,
                "arguments": {
                    "uploaded_s3_object_id": s3_object.id,
                    "analysis_variable": analysis_variable,
                },
            },
        )

        assert resp_job.raise_for_status()
        resp_json = resp_job.json()
        _logger.debug("Response:\n%s", pprint.pformat(resp_json))
        workflow_job_id = resp_json["id"]

    async with with_rabbit() as rabbit:
        await asyncio.wait_for(
            _wait_for_matrix_profile_message(rabbit, analysis_variable),
            timeout=_DEFAULT_MESSAGE_TIMEOUT_SECS,
        )

    with TestClient(app) as client:
        result_key = uuid.uuid4().hex

        resp_update = client.patch(
            f"/job/{workflow_job_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"results": {result_key: result_key}},
        )

        assert resp_update.raise_for_status()

    async with with_session() as session:
        workflow_job = (
            (
                await session.execute(
                    select(WorkflowJob).where(WorkflowJob.id == workflow_job_id)
                )
            )
            .scalars()
            .one_or_none()
        )

        assert workflow_job
        assert workflow_job.creator_username
        assert workflow_job.results[result_key]
        assert workflow_job.finalised_at
