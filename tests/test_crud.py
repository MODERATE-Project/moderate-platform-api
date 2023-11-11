import logging
import pprint
import uuid

import pytest
from fastapi.testclient import TestClient

from moderate_api.entities.asset import AssetCreate
from moderate_api.main import app
from tests.db import DB_SKIP_REASON, is_db_online

pytestmark = pytest.mark.skipif(is_db_online() is False, reason=DB_SKIP_REASON)

_logger = logging.getLogger(__name__)


def _create_asset(the_client: TestClient, the_access_token: str) -> dict:
    asset = AssetCreate(uuid=uuid.uuid4().hex, name=uuid.uuid4().hex)

    response = the_client.post(
        "/asset",
        headers={"Authorization": f"Bearer {the_access_token}"},
        data=asset.json(),
    )

    assert response.raise_for_status()
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert resp_json["uuid"] == asset.uuid
    assert resp_json["name"] == asset.name
    return resp_json


@pytest.mark.asyncio
async def test_create(access_token):
    """Test that assets can be created."""

    with TestClient(app) as client:
        assert _create_asset(client, access_token)


@pytest.mark.asyncio
async def test_read(access_token):
    with TestClient(app) as client:
        asset_created = _create_asset(client, access_token)
        asset_id = asset_created.get("id")

        response = client.get(
            f"/asset/{asset_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.raise_for_status()
        resp_json = response.json()
        _logger.debug("Response:\n%s", pprint.pformat(resp_json))
