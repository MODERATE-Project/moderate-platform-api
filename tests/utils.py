import logging
import pprint
import uuid
from typing import Optional

from fastapi.testclient import TestClient

from moderate_api.entities.asset import AssetCreate

_logger = logging.getLogger(__name__)


def create_asset(
    the_client: TestClient, the_access_token: str, the_uuid: Optional[str] = None
) -> dict:
    the_uuid = the_uuid or uuid.uuid4().hex
    asset = AssetCreate(uuid=the_uuid, name=uuid.uuid4().hex)

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
