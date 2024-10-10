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

from fastapi.testclient import TestClient

from moderate_api.authz.token import decode_token
from moderate_api.config import get_settings
from moderate_api.entities.access_request.models import AccessRequestCreate
from moderate_api.entities.asset.models import AssetCreate
from moderate_api.entities.user.models import UserMetaCreate
from moderate_api.main import app

_logger = logging.getLogger(__name__)


def create_user_meta(the_client: TestClient, the_access_token: str, **kwargs) -> dict:
    create_kwargs = {
        "username": str(uuid.uuid4()),
        "trust_did": "did:web:trust",
        "meta": {"hello": "world", "random": random.randint(0, 1000)},
    }

    create_kwargs.update(kwargs)
    user_meta = UserMetaCreate(**create_kwargs)

    response = the_client.post(
        "/user",
        headers={"Authorization": f"Bearer {the_access_token}"},
        data=user_meta.json(),
    )

    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert response.raise_for_status()
    assert resp_json["username"] == user_meta.username
    assert isinstance(resp_json["meta"], dict)
    return resp_json


def read_user_meta(
    the_client: TestClient, the_access_token: str, the_user_meta: dict
) -> dict:
    user_meta_id = the_user_meta["id"]

    response = the_client.get(
        f"/user/{user_meta_id}",
        headers={"Authorization": f"Bearer {the_access_token}"},
    )

    assert response.raise_for_status()
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    return resp_json


def create_asset(
    the_client: TestClient,
    the_access_token: str,
    the_uuid: Optional[str] = None,
    asset_kwargs: Optional[dict] = None,
) -> dict:
    the_uuid = the_uuid or str(uuid.uuid4())
    kwargs = {"name": str(uuid.uuid4()), "uuid": the_uuid}
    kwargs.update(asset_kwargs or {})
    asset = AssetCreate(**kwargs)

    response = the_client.post(
        "/asset",
        headers={"Authorization": f"Bearer {the_access_token}"},
        data=asset.json(),
    )

    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert response.raise_for_status()
    assert resp_json["uuid"] == asset.uuid
    assert resp_json["name"] == asset.name
    return resp_json


def read_asset(the_client: TestClient, the_access_token: str, the_asset: dict) -> dict:
    asset_id = the_asset["id"]

    response = the_client.get(
        f"/asset/{asset_id}",
        headers={"Authorization": f"Bearer {the_access_token}"},
    )

    assert response.raise_for_status()
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert resp_json["id"] == asset_id
    assert resp_json["uuid"] == the_asset["uuid"]
    assert resp_json["name"] == the_asset["name"]
    return resp_json


def update_asset(
    the_client: TestClient,
    the_access_token: str,
    the_asset: dict,
    new_name: str,
    new_uuid: Optional[str] = None,
) -> dict:
    asset_id = the_asset["id"]
    update_doc = {"name": new_name}

    if new_uuid:
        update_doc["uuid"] = new_uuid

    response = the_client.patch(
        f"/asset/{asset_id}",
        headers={"Authorization": f"Bearer {the_access_token}"},
        json=update_doc,
    )

    assert response.raise_for_status()
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert resp_json["id"] == asset_id
    assert resp_json["uuid"] == the_asset["uuid"]
    assert resp_json["name"] == new_name
    return resp_json


def delete_asset(the_client: TestClient, the_access_token: str, the_asset: dict):
    asset_id = the_asset["id"]

    response = the_client.delete(
        f"/asset/{asset_id}",
        headers={"Authorization": f"Bearer {the_access_token}"},
    )

    assert response.raise_for_status()


@contextmanager
def temp_csv(num_cols: Optional[int] = None, num_rows: Optional[int] = None):
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


def post_upload_asset_object(
    client: TestClient,
    the_asset: dict,
    the_access_token: str,
    fh: BufferedReader,
    form: Optional[dict] = None,
    upload_prefix: Optional[str] = None,
):
    upload_name = "{}-{}.csv".format(upload_prefix or "upload", str(uuid.uuid4()))

    response = client.post(
        "/asset/{}/object".format(the_asset["id"]),
        headers={"Authorization": f"Bearer {the_access_token}"},
        files={"obj": (upload_name, fh)},
        data=form or {},
    )

    assert response.raise_for_status()
    return response


def upload_test_files(
    the_access_token: str,
    num_files: Optional[int] = 2,
    form: Optional[dict] = None,
    the_asset: Optional[dict] = None,
    upload_prefix: Optional[str] = None,
) -> str:
    with ExitStack() as stack:
        client = stack.enter_context(TestClient(app))

        temp_csv_paths = []

        for _ in range(num_files):
            temp_csv_path = stack.enter_context(temp_csv())
            temp_csv_paths.append(temp_csv_path)

        the_asset = (
            create_asset(client, the_access_token) if not the_asset else the_asset
        )

        for temp_path in temp_csv_paths:
            with open(temp_path, "rb") as fh:
                response = post_upload_asset_object(
                    client,
                    the_asset,
                    the_access_token,
                    fh,
                    form=form,
                    upload_prefix=upload_prefix,
                )

                res_json = response.json()
                _logger.info("Response:\n%s", pprint.pformat(res_json))

        return the_asset["id"]


async def create_access_request(
    the_client: TestClient,
    the_access_token: str,
    access_request_kwargs: Optional[dict] = None,
    asset_id: Optional[int] = None,
) -> dict:
    asset_id = asset_id or create_asset(the_client, the_access_token)["id"]
    random_requester_username = str(uuid.uuid4())

    kwargs = {
        "requester_username": random_requester_username,
        "asset_id": asset_id,
    }

    kwargs.update(access_request_kwargs or {})
    asset = AccessRequestCreate(**kwargs)

    response = the_client.post(
        "/request",
        headers={"Authorization": f"Bearer {the_access_token}"},
        data=asset.json(),
    )

    decoded_token = await decode_token(the_access_token, settings=get_settings())
    expected_username = decoded_token["preferred_username"]

    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert response.raise_for_status()
    assert resp_json["allowed"] is None
    assert resp_json["asset_id"] == asset_id
    assert expected_username != random_requester_username
    assert resp_json["requester_username"] == expected_username
    return resp_json


def read_access_request(
    the_client: TestClient, the_access_token: str, access_request_id: int
) -> dict:
    response = the_client.get(
        f"/request/{access_request_id}",
        headers={"Authorization": f"Bearer {the_access_token}"},
    )

    assert response.raise_for_status()
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    return resp_json
