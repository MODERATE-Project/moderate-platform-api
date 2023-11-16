import csv
import logging
import os
import pprint
import random
import tempfile
import uuid
from contextlib import contextmanager
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from moderate_api.entities.asset import AssetCreate
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


@pytest.mark.asyncio
async def test_upload_object(access_token):
    with TestClient(app) as client, _temp_csv() as temp_csv_path:
        the_asset = _create_asset(client, access_token)

        with open(temp_csv_path, "rb") as fh:
            upload_name = "upload-{}.csv".format(uuid.uuid4().hex)

            response = client.post(
                "/asset/{}/object".format(the_asset["id"]),
                headers={"Authorization": f"Bearer {access_token}"},
                files={"obj": (upload_name, fh)},
            )

            assert response.raise_for_status()
            _logger.debug("Response:\n%s", pprint.pformat(response.json()))
