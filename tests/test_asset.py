import logging
import pprint
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from moderate_api.entities.asset import AssetCreate
from moderate_api.main import app
from tests.utils import create_asset

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
