import json
import logging
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from moderate_api.db import with_session
from moderate_api.entities.access_request.models import AccessRequest
from moderate_api.main import app
from tests.utils import create_access_request, read_access_request

_logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_create_one(access_token):
    with TestClient(app) as client:
        assert await create_access_request(client, access_token)


@pytest.mark.asyncio
async def test_relationship(access_token):
    with TestClient(app) as client:
        created_dict = await create_access_request(client, access_token)

    async with with_session() as session:
        stmt = select(AccessRequest).where(AccessRequest.id == created_dict["id"])
        result = await session.execute(stmt)
        access_request = result.scalars().one_or_none()

    assert access_request.asset.id == created_dict["asset_id"]


@pytest.mark.asyncio
async def test_approve_permission(access_token):
    with TestClient(app) as client:
        created_dict = await create_access_request(client, access_token)
        access_request_id = created_dict["id"]

        resp_one = client.post(
            f"/request/{access_request_id}/permission",
            headers={"Authorization": f"Bearer {access_token}"},
            data=json.dumps({"allowed": True}),
        )

        assert resp_one.raise_for_status()

        async with with_session() as session:
            stmt = select(AccessRequest).where(AccessRequest.id == access_request_id)
            result = await session.execute(stmt)
            access_request_one = result.scalars().one_or_none()
            assert access_request_one.allowed is True
            assert access_request_one.validated_at
            assert access_request_one.validator_username

        resp_two = client.post(
            f"/request/{access_request_id}/permission",
            headers={"Authorization": f"Bearer {access_token}"},
            data=json.dumps({"allowed": False}),
        )

        assert resp_two.raise_for_status()

        async with with_session() as session:
            stmt = select(AccessRequest).where(AccessRequest.id == access_request_id)
            result = await session.execute(stmt)
            access_request_two = result.scalars().one_or_none()
            _logger.debug("AccessRequest (2): %s", access_request_two)
            assert access_request_two.allowed is False
            assert access_request_two.validated_at > access_request_one.validated_at
            assert access_request_two.validator_username


@pytest.mark.parametrize(
    "access_token",
    [{"is_admin": False}],
    indirect=True,
)
@pytest.mark.asyncio
async def test_permission_access(access_token):
    with TestClient(app) as client:
        created_dict = await create_access_request(client, access_token)
        access_request_id = created_dict["id"]

        async with with_session() as session:
            stmt = select(AccessRequest).where(AccessRequest.id == access_request_id)
            result = await session.execute(stmt)
            access_request = result.scalars().one_or_none()
            access_request.asset.username = uuid.uuid4().hex
            session.add(access_request)
            await session.commit()

        resp = client.post(
            f"/request/{access_request_id}/permission",
            headers={"Authorization": f"Bearer {access_token}"},
            data=json.dumps({"allowed": True}),
        )

        with pytest.raises(httpx.HTTPStatusError):
            resp.raise_for_status()


@pytest.mark.parametrize(
    "access_token",
    [{"is_admin": False}],
    indirect=True,
)
@pytest.mark.asyncio
async def test_read_access(access_token):
    with TestClient(app) as client:
        created_dict = await create_access_request(client, access_token)
        access_request_id = created_dict["id"]
        assert read_access_request(client, access_token, access_request_id)

        async with with_session() as session:
            stmt = select(AccessRequest).where(AccessRequest.id == access_request_id)
            result = await session.execute(stmt)
            access_request = result.scalars().one_or_none()
            access_request.requester_username = uuid.uuid4().hex
            access_request.asset.username = uuid.uuid4().hex
            session.add(access_request)
            await session.commit()

        with pytest.raises(httpx.HTTPStatusError):
            read_access_request(client, access_token, access_request_id)

        resp_permission = client.post(
            f"/request/{access_request_id}/permission",
            headers={"Authorization": f"Bearer {access_token}"},
            data=json.dumps({"allowed": True}),
        )

        with pytest.raises(httpx.HTTPStatusError):
            resp_permission.raise_for_status()
