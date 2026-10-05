import datetime
import hashlib
import json
import logging
import pprint
import random
import uuid
from contextlib import ExitStack
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from moderate_api.config import get_settings
from moderate_api.db import with_session
from moderate_api.entities.asset.models import Asset, UploadedS3Object
from moderate_api.entities.asset.router import get_asset_presigned_urls
from moderate_api.main import app
from tests.utils import (
    create_asset,
    post_upload_asset_object,
    temp_csv,
    upload_test_files,
)

_logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_s3_client_dep(s3):  # type: ignore[no-untyped-def]
    res_buckets = await s3.list_buckets()
    _logger.info("Buckets:\n%s", pprint.pformat(res_buckets))
    assert "Buckets" in res_buckets


@pytest.mark.asyncio
async def test_upload_object(access_token):  # type: ignore[no-untyped-def]
    upload_test_files(access_token)


@pytest.mark.asyncio
async def test_presigned_urls(access_token, s3):  # type: ignore[no-untyped-def]
    num_files = random.randint(2, 5)
    asset_id = upload_test_files(access_token, num_files=num_files)

    async with with_session() as session:
        assert session
        the_asset = await session.get(Asset, asset_id)
        assert the_asset.id == asset_id
        urls = await get_asset_presigned_urls(s3=s3, asset=the_asset)
        _logger.info("Presigned URLs:\n%s", pprint.pformat(urls))
        assert len(urls) == num_files


def _upload_and_get_download_url(
    client: TestClient, access_token: str
) -> tuple[bytes, str]:
    payload = b"timestamp,value\n2026-01-01,42\n"
    asset = create_asset(client, access_token)
    headers = {"Authorization": f"Bearer {access_token}"}
    upload = client.post(
        f"/asset/{asset['id']}/object",
        headers=headers,
        files={"obj": ("dataset.csv", payload, "text/csv")},
    )
    upload.raise_for_status()
    response = client.get(f"/asset/{asset['id']}/download-urls", headers=headers)
    response.raise_for_status()
    urls = response.json()
    assert len(urls) == 1
    return payload, urls[0]["download_url"]


@pytest.mark.asyncio
@pytest.mark.parametrize("use_public_endpoint", [False, True])
async def test_download_route(
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
    use_public_endpoint: bool,
) -> None:
    """Fetch unchanged signed URLs to verify public signing and storage fallback."""
    settings = get_settings()
    assert settings.s3 is not None
    endpoint = urlsplit(settings.s3.endpoint_url)
    expected_host = endpoint.netloc
    if use_public_endpoint:
        assert endpoint.hostname in {"localhost", "127.0.0.1"}
        public_host = "127.0.0.1" if endpoint.hostname == "localhost" else "localhost"
        expected_host = f"{public_host}:{endpoint.port}"
        public_endpoint = endpoint._replace(netloc=expected_host).geturl()
        monkeypatch.setenv("MODERATE_API_S3__PUBLIC_ENDPOINT_URL", public_endpoint)
    else:
        monkeypatch.delenv("MODERATE_API_S3__PUBLIC_ENDPOINT_URL", raising=False)

    with TestClient(app) as client:
        payload, download_url = _upload_and_get_download_url(client, access_token)

    assert urlsplit(download_url).netloc == expected_host
    response = httpx.get(download_url, trust_env=False)
    response.raise_for_status()
    assert response.content == payload


@pytest.mark.asyncio
async def test_https_presigning_keeps_uploads_internal(
    access_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Uploads and signing must succeed without contacting the public endpoint."""
    monkeypatch.setenv(
        "MODERATE_API_S3__PUBLIC_ENDPOINT_URL", "https://downloads.invalid:8443"
    )
    monkeypatch.setenv("MODERATE_API_S3__USE_SSL", "false")

    with TestClient(app) as client:
        _, download_url = _upload_and_get_download_url(client, access_token)

    endpoint = urlsplit(download_url)
    assert endpoint.scheme == "https"
    assert endpoint.netloc == "downloads.invalid:8443"


@pytest.mark.asyncio
async def test_download_route_filters_by_object_id(
    access_token,
):  # type: ignore[no-untyped-def]
    asset_id = upload_test_files(access_token, num_files=2)

    async with with_session() as session:
        the_asset = await session.get(Asset, asset_id)
        assert the_asset is not None
        selected_object = the_asset.objects[0]

    with TestClient(app) as client:
        response = client.get(
            f"/asset/{asset_id}/download-urls",
            params={"object_id": selected_object.id},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.raise_for_status()
        res_json = response.json()
        _logger.info("Filtered response:\n%s", pprint.pformat(res_json))
        assert len(res_json) == 1
        assert res_json[0]["key"] == selected_object.key


async def _get_num_uploaded_objects() -> int:
    async with with_session() as session:
        stmt = select(UploadedS3Object)
        result = await session.execute(stmt)
        uploaded_objects = result.all()
        return len(uploaded_objects)


@pytest.mark.asyncio
async def test_delete_asset_with_objects(access_token):  # type: ignore[no-untyped-def]
    num_files = 2
    asset_id = upload_test_files(access_token, num_files=num_files)
    assert await _get_num_uploaded_objects() == num_files

    with TestClient(app) as client:
        response = client.delete(
            f"/asset/{asset_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.raise_for_status()

    assert await _get_num_uploaded_objects() == 0


@pytest.mark.asyncio
async def test_delete_object_from_asset(access_token):  # type: ignore[no-untyped-def]
    num_files = random.randint(2, 5)
    asset_id = upload_test_files(access_token, num_files=num_files)

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
async def test_upload_object_with_metadata(access_token):  # type: ignore[no-untyped-def]
    tags_dict = {
        "uid": str(uuid.uuid4()),
        "dtime": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    series_id = str(uuid.uuid4())

    asset_id = upload_test_files(
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
async def test_object_hashes(access_token):  # type: ignore[no-untyped-def]
    with ExitStack() as stack:
        client = stack.enter_context(TestClient(app))
        temp_csv_paths = []
        hashes = []

        for _ in range(1):
            temp_csv_path = stack.enter_context(
                temp_csv(num_rows=random.randint(int(1e3), int(1e4)))
            )

            temp_csv_paths.append(temp_csv_path)
            hashes.append(_get_file_hash(temp_csv_path))

        the_asset = create_asset(client, access_token)

        for idx, temp_path in enumerate(temp_csv_paths):
            with open(temp_path, "rb") as fh:
                response = post_upload_asset_object(client, the_asset, access_token, fh)
                res_json = response.json()
                _logger.info("Response:\n%s", pprint.pformat(res_json))
                assert res_json["sha256_hash"] == hashes[idx]

        assert the_asset
