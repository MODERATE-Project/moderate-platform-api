import json
import logging
import pprint
import random
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from moderate_api.main import app
from tests.utils import create_asset, delete_asset, read_asset, update_asset

_logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_create_one(access_token):
    with TestClient(app) as client:
        assert create_asset(client, access_token)


@pytest.mark.asyncio
async def test_read_one(access_token):
    with TestClient(app) as client:
        asset_created = create_asset(client, access_token)
        assert read_asset(client, access_token, asset_created)


@pytest.mark.asyncio
async def test_update_one(access_token):
    with TestClient(app) as client:
        asset_created = create_asset(client, access_token)
        new_name = str(uuid.uuid4())
        asset_updated = update_asset(client, access_token, asset_created, new_name)
        asset_read = read_asset(client, access_token, asset_updated)
        assert asset_read["name"] == new_name


@pytest.mark.asyncio
async def test_delete_one(access_token):
    with TestClient(app) as client:
        asset_created = create_asset(client, access_token)

        for _ in range(2):
            assert read_asset(client, access_token, asset_created)

        delete_asset(client, access_token, asset_created)

        with pytest.raises(httpx.HTTPStatusError):
            read_asset(client, access_token, asset_created)


@pytest.mark.asyncio
async def test_read_many_with_filters(access_token):
    with TestClient(app) as client:
        assets_created = [create_asset(client, access_token) for _ in range(5)]
        assets_selected = random.sample(assets_created, 3)

        filters_list = [
            ["name", "in", json.dumps([a["name"] for a in assets_selected])]
        ]

        filters_json_str = json.dumps(filters_list)

        _logger.debug("Query filters (as list):\n%s", pprint.pformat(filters_list))
        _logger.debug("Query filters (JSON-encoded):\n%s", filters_json_str)

        response = client.get(
            f"/asset",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"filters": filters_json_str},
        )

        assert response.raise_for_status()
        resp_json = response.json()
        _logger.debug("Response:\n%s", pprint.pformat(resp_json))
        assert len(resp_json) == len(assets_selected)
        assert all([a["id"] in [r["id"] for r in resp_json] for a in assets_selected])


@pytest.mark.asyncio
async def test_read_many_with_sorts(access_token):
    with TestClient(app) as client:
        assets_created = [create_asset(client, access_token) for _ in range(10)]

        sorts_list = [
            ["uuid", "asc"],
            ["name", "asc"],
        ]

        sorts_json_str = json.dumps(sorts_list)

        response = client.get(
            f"/asset",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"sorts": sorts_json_str},
        )

        assert response.raise_for_status()
        resp_json = response.json()
        _logger.debug("Response:\n%s", pprint.pformat(resp_json))
        assets_expected = sorted(assets_created, key=lambda a: (a["uuid"], a["name"]))
        assert len(resp_json) == len(assets_expected)
        assert all([a["id"] == r["id"] for a, r in zip(assets_expected, resp_json)])
