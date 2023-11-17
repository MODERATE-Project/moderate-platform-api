import csv
import logging
import os
import pprint
import random
import tempfile
import uuid
from contextlib import ExitStack, contextmanager
from io import BufferedReader
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from moderate_api.db import with_session
from moderate_api.entities.asset import (
    Asset,
    AssetCreate,
    UploadedS3Object,
    get_asset_presigned_urls,
)
from moderate_api.main import app

_logger = logging.getLogger(__name__)


@contextmanager
def _temp_csv(num_cols: Optional[int] = None, num_rows: Optional[int] = None) -> str:
    num_rows = num_rows or random.randint(200, 400)
    num_cols = num_cols or random.randint(100, 200)
    abs_path = os.path.join(tempfile.gettempdir(), "{}.csv".format(uuid.uuid4().hex))

    _logger.info(
        "Creating temp CSV file (rows=%s) (cols=%s): %s",
        num_rows,
        num_cols,
        abs_path,
    )

    with open(abs_path, mode="w", newline="") as csv_file:
        fieldnames = [uuid.uuid4().hex for _ in range(num_cols)]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for _ in range(num_rows):
            writer.writerow({name: uuid.uuid4().hex for name in fieldnames})

    _logger.info("Created temp CSV file: %s", abs_path)

    yield abs_path

    try:
        os.remove(abs_path)
        _logger.debug("Removed temp CSV file: %s", abs_path)
    except Exception:
        _logger.warning("Failed to remove temp CSV file", exc_info=True)


def _create_asset(the_client: TestClient, the_access_token: str) -> dict:
    asset = AssetCreate(uuid=uuid.uuid4().hex, name=uuid.uuid4().hex)

    response = the_client.post(
        "/asset",
        headers={"Authorization": f"Bearer {the_access_token}"},
        data=asset.json(),
    )

    assert response.raise_for_status()
    return response.json()


@pytest.mark.asyncio
async def test_s3_client_dep(s3):
    res_buckets = await s3.list_buckets()
    _logger.info("Buckets:\n%s", pprint.pformat(res_buckets))
    assert "Buckets" in res_buckets


def _post_upload(
    client: TestClient, the_asset: dict, the_access_token: str, fh: BufferedReader
):
    upload_name = "upload-{}.csv".format(uuid.uuid4().hex)

    response = client.post(
        "/asset/{}/object".format(the_asset["id"]),
        headers={"Authorization": f"Bearer {the_access_token}"},
        files={"obj": (upload_name, fh)},
    )

    assert response.raise_for_status()
    return response


def _upload_test_files(the_access_token: str, num_files: Optional[int] = 2) -> str:
    with ExitStack() as stack:
        client = stack.enter_context(TestClient(app))

        temp_csv_paths = []

        for _ in range(num_files):
            temp_csv_path = stack.enter_context(_temp_csv())
            temp_csv_paths.append(temp_csv_path)

        the_asset = _create_asset(client, the_access_token)

        for temp_path in temp_csv_paths:
            with open(temp_path, "rb") as fh:
                response = _post_upload(client, the_asset, the_access_token, fh)
                res_json = response.json()
                _logger.info("Response:\n%s", pprint.pformat(res_json))

        return the_asset["id"]


@pytest.mark.asyncio
async def test_upload_object(access_token):
    _upload_test_files(access_token)


@pytest.mark.asyncio
async def test_presigned_urls(access_token, s3):
    num_files = random.randint(2, 5)
    asset_id = _upload_test_files(access_token, num_files=num_files)

    async with with_session() as session:
        assert session
        the_asset = await session.get(Asset, asset_id)
        assert the_asset.id == asset_id
        urls = await get_asset_presigned_urls(s3=s3, asset=the_asset)
        _logger.info("Presigned URLs:\n%s", pprint.pformat(urls))
        assert len(urls) == num_files


@pytest.mark.asyncio
async def test_download_route(access_token):
    num_files = random.randint(2, 5)
    asset_id = _upload_test_files(access_token, num_files=num_files)

    with TestClient(app) as client:
        response = client.get(
            "/asset/{}/download-urls".format(asset_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.raise_for_status()
        res_json = response.json()
        _logger.info("Response:\n%s", pprint.pformat(res_json))
        assert len(res_json) == num_files


async def _get_num_uploaded_objects() -> int:
    async with with_session() as session:
        stmt = select(UploadedS3Object)
        result = await session.execute(stmt)
        uploaded_objects = result.all()
        return len(uploaded_objects)


@pytest.mark.asyncio
async def test_delete_asset_with_objects(access_token):
    num_files = 2
    asset_id = _upload_test_files(access_token, num_files=num_files)
    assert await _get_num_uploaded_objects() == num_files

    with TestClient(app) as client:
        response = client.delete(
            f"/asset/{asset_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.raise_for_status()

    assert await _get_num_uploaded_objects() == 0
