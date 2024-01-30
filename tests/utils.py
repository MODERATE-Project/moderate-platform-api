import logging
import pprint
import random
import uuid
from typing import Optional

from fastapi.testclient import TestClient

from moderate_api.entities.asset.models import AssetCreate
from moderate_api.entities.user.models import UserMetaCreate

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
    the_client: TestClient, the_access_token: str, the_uuid: Optional[str] = None
) -> dict:
    the_uuid = the_uuid or str(uuid.uuid4())
    asset = AssetCreate(uuid=the_uuid, name=str(uuid.uuid4()))

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
