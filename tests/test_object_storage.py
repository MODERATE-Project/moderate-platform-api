import csv
import datetime
import hashlib
import json
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
from moderate_api.entities.asset.models import Asset, AssetCreate, UploadedS3Object
from moderate_api.entities.asset.router import get_asset_presigned_urls
from moderate_api.main import app

_logger = logging.getLogger(__name__)


@contextmanager
def _temp_csv(num_cols: Optional[int] = None, num_rows: Optional[int] = None) -> str:
    num_rows = num_rows or random.randint(200, 400)
    num_cols = num_cols or random.randint(100, 200)
    abs_path = os.path.join(tempfile.gettempdir(), "{}.csv".format(str(uuid.uuid4())))

    _logger.info(
        "Creating temp CSV file (rows=%s) (cols=%s): %s",
        num_rows,
        num_cols,
        abs_path,
    )

    with open(abs_path, mode="w", newline="") as csv_file:
        fieldnames = [str(uuid.uuid4()) for _ in range(num_cols)]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for _ in range(num_rows):
            writer.writerow({name: str(uuid.uuid4()) for name in fieldnames})

    _logger.info("Created temp CSV file: %s", abs_path)

    yield abs_path

    try:
        os.remove(abs_path)
        _logger.debug("Removed temp CSV file: %s", abs_path)
    except Exception:
        _logger.warning("Failed to remove temp CSV file", exc_info=True)


def _create_asset(the_client: TestClient, the_access_token: str) -> dict:
    asset = AssetCreate(uuid=str(uuid.uuid4()), name=str(uuid.uuid4()))

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
    client: TestClient,
    the_asset: dict,
    the_access_token: str,
    fh: BufferedReader,
    form: Optional[dict] = None,
):
    upload_name = "upload-{}.csv".format(str(uuid.uuid4()))

    response = client.post(
        "/asset/{}/object".format(the_asset["id"]),
        headers={"Authorization": f"Bearer {the_access_token}"},
        files={"obj": (upload_name, fh)},
        data=form or {},
    )

    assert response.raise_for_status()
    return response


def _upload_test_files(
    the_access_token: str, num_files: Optional[int] = 2, form: Optional[dict] = None
) -> str:
    with ExitStack() as stack:
        client = stack.enter_context(TestClient(app))

        temp_csv_paths = []

        for _ in range(num_files):
            temp_csv_path = stack.enter_context(_temp_csv())
            temp_csv_paths.append(temp_csv_path)

        the_asset = _create_asset(client, the_access_token)

        for temp_path in temp_csv_paths:
            with open(temp_path, "rb") as fh:
                response = _post_upload(
                    client, the_asset, the_access_token, fh, form=form
                )

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


@pytest.mark.asyncio
async def test_delete_object_from_asset(access_token):
    num_files = random.randint(2, 5)
    asset_id = _upload_test_files(access_token, num_files=num_files)

    async with with_session() as session:
        stmt = select(Asset).where(Asset.id == asset_id)
        result = await session.execute(stmt)
        the_asset = result.one_or_none()[0]

        assert len(the_asset.objects) == num_files
        deleted_object = random.sample(the_asset.objects, 1)[0]
        _logger.info("Asset object to delete:\n%s", deleted_object)

        with TestClient(app) as client:
            res = client.delete(
                f"/asset/{the_asset.id}/object/{deleted_object.id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert res.raise_for_status()
            res_json = res.json()
            assert res_json

        await session.refresh(the_asset)
        assert len(the_asset.objects) == num_files - 1
        assert all(obj.id != deleted_object.id for obj in the_asset.objects)


@pytest.mark.asyncio
async def test_upload_object_with_metadata(access_token):
    tags_dict = {
        "uid": str(uuid.uuid4()),
        "dtime": datetime.datetime.utcnow().isoformat(),
    }

    series_id = str(uuid.uuid4())

    asset_id = _upload_test_files(
        access_token,
        num_files=1,
        form={"tags": json.dumps(tags_dict), "series_id": series_id},
    )

    async with with_session() as session:
        stmt = select(Asset).where(Asset.id == asset_id)
        result = await session.execute(stmt)
        the_asset = result.one_or_none()[0]
        assert len(the_asset.objects) == 1
        the_object = the_asset.objects[0]
        assert the_object.tags == tags_dict
        assert the_object.series_id == series_id


def _get_file_hash(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        byte_block = f.read()

        _logger.info(
            "Hashing file (%s MiB): %s",
            round(len(byte_block) / (1024.0**2), 2),
            file_path,
        )

        sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


@pytest.mark.asyncio
async def test_object_hashes(access_token):
    with ExitStack() as stack:
        client = stack.enter_context(TestClient(app))
        temp_csv_paths = []
        hashes = []

        for _ in range(1):
            temp_csv_path = stack.enter_context(
                _temp_csv(num_rows=random.randint(int(1e3), int(1e4)))
            )

            temp_csv_paths.append(temp_csv_path)
            hashes.append(_get_file_hash(temp_csv_path))

        the_asset = _create_asset(client, access_token)

        for idx, temp_path in enumerate(temp_csv_paths):
            with open(temp_path, "rb") as fh:
                response = _post_upload(client, the_asset, access_token, fh)
                res_json = response.json()
                _logger.info("Response:\n%s", pprint.pformat(res_json))
                assert res_json["sha256_hash"] == hashes[idx]

        assert the_asset
