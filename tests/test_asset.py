import logging
import pprint
import random
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from moderate_api.db import with_session
from moderate_api.entities.asset.models import (
    Asset,
    AssetAccessLevels,
    AssetCreate,
    UploadedS3Object,
    find_s3object_pending_quality_check,
    update_s3object_quality_check_flag,
)
from moderate_api.main import app
from tests.utils import create_asset, upload_test_files

_logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_unique_uuid(access_token):
    with TestClient(app) as client:
        first_asset = create_asset(client, access_token)

        with pytest.raises(httpx.HTTPStatusError):
            create_asset(client, access_token, the_uuid=first_asset["uuid"])

        second_asset = create_asset(client, access_token)
        assert first_asset["uuid"] != second_asset["uuid"]


@pytest.mark.asyncio
async def test_auto_uuid(access_token):
    with TestClient(app) as client:
        asset = AssetCreate(name=str(uuid.uuid4()))

        response = client.post(
            "/asset",
            headers={"Authorization": f"Bearer {access_token}"},
            data=asset.json(),
        )

        resp_json = response.json()
        _logger.debug("Response:\n%s", pprint.pformat(resp_json))
        assert response.raise_for_status()
        assert resp_json["uuid"]


@pytest.mark.asyncio
async def test_asset_object_quality_check(access_token):
    asset_id = upload_test_files(access_token, num_files=4)

    async with with_session() as session:
        stmt = select(UploadedS3Object).where(UploadedS3Object.asset_id == asset_id)
        result = await session.execute(stmt)
        s3objects = result.scalars().all()
        s3obj_ids = [obj.id for obj in s3objects]

        pending = await find_s3object_pending_quality_check(session=session)
        assert not pending or len(pending) == 0

        await update_s3object_quality_check_flag(
            session=session, ids=s3obj_ids[:-1], value=True
        )

        pending = await find_s3object_pending_quality_check(session=session)
        assert len(pending) == (len(s3objects) - 1)

        await update_s3object_quality_check_flag(
            session=session, ids=s3obj_ids[0], value=False
        )

        pending = await find_s3object_pending_quality_check(session=session)
        assert len(pending) == (len(s3objects) - 2)


@pytest.mark.parametrize(
    "access_token",
    [{"is_admin": False}],
    indirect=True,
)
@pytest.mark.asyncio
async def test_asset_object_quality_check_endpoints(access_token):
    num_files = 4
    asset_id = upload_test_files(access_token, num_files=num_files)

    async with with_session() as session:
        stmt = select(UploadedS3Object).where(UploadedS3Object.asset_id == asset_id)
        result = await session.execute(stmt)
        s3objects = result.scalars().all()
        s3obj_ids = [obj.id for obj in s3objects]

    forbidden_asset_id = upload_test_files(access_token, num_files=2)

    async with with_session() as session:
        stmt = select(Asset).where(Asset.id == forbidden_asset_id)
        result = await session.execute(stmt)
        asset = result.scalars().one()
        asset.username = uuid.uuid4().hex
        session.add(asset)
        await session.commit()
        forbidden_s3obj_ids = [obj.id for obj in asset.objects]

    headers = {"Authorization": f"Bearer {access_token}"}

    with TestClient(app) as client:
        resp_get_before = client.get("/asset/object/quality-check", headers=headers)
        assert resp_get_before.raise_for_status()
        resp_json = resp_get_before.json()
        _logger.info("Response:\n%s", pprint.pformat(resp_json))
        assert len(resp_json) == 0

        num_flagged = 2

        post_body = {
            "asset_object_id": [*s3obj_ids[:num_flagged], *forbidden_s3obj_ids],
            "pending_quality_check": True,
        }

        resp_post = client.post(
            "/asset/object/quality-check", headers=headers, json=post_body
        )

        assert resp_post.raise_for_status()

        resp_get_after = client.get("/asset/object/quality-check", headers=headers)
        assert resp_get_after.raise_for_status()
        resp_json = resp_get_after.json()
        _logger.info("Response:\n%s", pprint.pformat(resp_json))
        assert len(resp_json) == num_flagged
        assert len(post_body["asset_object_id"]) > num_flagged
        assert all(item["asset_id"] != forbidden_asset_id for item in resp_json)


@pytest.mark.asyncio
async def test_public_read_private_asset(access_token):
    """Public anonymous users should not be able to read private assets."""

    asset_id = upload_test_files(access_token, num_files=random.randint(1, 4))

    async with with_session() as session:
        stmt = select(Asset).where(Asset.id == asset_id)
        result = await session.execute(stmt)
        asset = result.scalars().one()
        assert asset.access_level == AssetAccessLevels.PRIVATE

    with TestClient(app) as client:
        resp_auth = client.get(
            "/asset/public", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert resp_auth.raise_for_status()
        data_auth = resp_auth.json()
        assert len(data_auth) == 1

        resp_public = client.get("/asset/public")
        assert resp_public.raise_for_status()
        data_public = resp_public.json()
        assert len(data_public) == 0
