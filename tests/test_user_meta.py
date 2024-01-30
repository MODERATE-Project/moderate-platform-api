import logging
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from moderate_api.db import with_session
from moderate_api.entities.user.models import UserMeta
from moderate_api.main import app
from tests.utils import create_user_meta, read_user_meta

_logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_regular_users_create_denied(access_token):
    with TestClient(app) as client:
        with pytest.raises(httpx.HTTPStatusError):
            create_user_meta(client, access_token)


@pytest.mark.parametrize(
    "access_token",
    [{"is_admin": True}],
    indirect=True,
)
@pytest.mark.asyncio
async def test_admins_create_allowed(access_token):
    with TestClient(app) as client:
        created_user_meta = create_user_meta(client, access_token)
        assert created_user_meta


_USERNAME = "test-user-{}".format(str(uuid.uuid4()))


@pytest.mark.parametrize(
    "access_token",
    [{"username": _USERNAME}],
    indirect=True,
)
@pytest.mark.asyncio
async def test_regular_users_read_limited(access_token):
    with TestClient(app) as client:
        username_rand = str(uuid.uuid4())

        async with with_session() as session:
            user_meta_denied = UserMeta(username=username_rand)
            user_meta_allowed = UserMeta(username=_USERNAME)
            session.add(user_meta_denied)
            session.add(user_meta_allowed)
            await session.commit()

            _logger.info(
                "Created:\n%s\n%s",
                user_meta_denied,
                user_meta_allowed,
            )

        user_meta_read = read_user_meta(client, access_token, user_meta_allowed.dict())
        assert user_meta_read["username"] == _USERNAME

        with pytest.raises(httpx.HTTPStatusError):
            read_user_meta(client, access_token, user_meta_denied.dict())
