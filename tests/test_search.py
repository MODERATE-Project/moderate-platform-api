import logging
import pprint
import random

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from moderate_api.db import with_session
from moderate_api.entities.asset.models import Asset
from moderate_api.main import app
from tests.utils import create_asset, upload_test_files

_logger = logging.getLogger(__name__)

_KWARGS_LIST = [
    {
        "name": "Building stock dataset",
        "description": "A dataset of building stock",
    },
    {
        "name": "Energy consumption dataset",
        "description": "A dataset of energy consumption",
    },
    {
        "name": "HVAC efficiency dataset",
        "description": "A dataset of HVAC efficiency",
    },
]


@pytest.mark.asyncio
async def test_asset_tsvector_column(access_token):  # type: ignore[no-untyped-def]
    with TestClient(app) as client:
        assets = [
            create_asset(
                the_client=client, the_access_token=access_token, asset_kwargs=item
            )
            for item in _KWARGS_LIST
        ]

    async with with_session() as session:
        for idx in range(len(assets)):
            name_search_query = " ".join(assets[idx]["name"].split()[:-1]).lower()
            stmt = select(Asset).filter(Asset.search_vector.match(name_search_query))
            result = await session.execute(stmt)
            found_assets = result.scalars().all()
            _logger.info("Found assets:\n%s", pprint.pformat(found_assets))
            assert found_assets[0].id == assets[idx]["id"]

        stmt = select(Asset).filter(Asset.search_vector.match("dataset"))
        result = await session.execute(stmt)
        found_assets = result.scalars().all()
        _logger.info("Found assets:\n%s", pprint.pformat(found_assets))
        assert len(found_assets) == len(assets)


@pytest.mark.asyncio
async def test_asset_search_endpoint(access_token):  # type: ignore[no-untyped-def]
    with TestClient(app) as client:
        assets = [
            create_asset(
                the_client=client, the_access_token=access_token, asset_kwargs=item
            )
            for item in _KWARGS_LIST
        ]

        for idx, asset in enumerate(assets):
            upload_test_files(
                access_token,
                num_files=random.randint(1, 4),
                the_asset=asset,
                upload_prefix=_KWARGS_LIST[idx]["name"],
            )

    headers = {"Authorization": f"Bearer {access_token}"}
    query = "dataset"

    with TestClient(app) as client:
        resp = client.get("/asset/search", params={"query": query}, headers=headers)
        assert resp.raise_for_status()
        resp_json = resp.json()
        _logger.info("Response:\n%s", pprint.pformat(resp_json))
        assert len(resp_json) == len(assets)

        resp = client.get("/asset/search", params={"query": query})
        assert resp.raise_for_status()
        resp_json = resp.json()
        _logger.info("Response:\n%s", pprint.pformat(resp_json))
        assert len(resp_json) == 0
