import logging
import pprint
import random
import uuid

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from moderate_api.db import with_session
from moderate_api.entities.asset.models import (
    Asset,
    AssetAccessLevels,
    AssetCreate,
    UploadedS3Object,
    find_s3object_pending_quality_check,
    update_s3object_quality_check_flag,
)
from moderate_api.main import app
from tests.utils import create_asset, upload_test_files

_logger = logging.getLogger(__name__)


def _make_access_token(username: str, *, is_admin: bool = False) -> str:
    roles = ["api_basic_access"]
    if is_admin:
        roles.append("api_admin")

    token_dict = {
        "preferred_username": username,
        "resource_access": {"apisix": {"roles": roles}},
        "realm_access": {"roles": []},
        "exp": 9999999999,
        "iat": 0,
    }
    return jwt.encode(token_dict, "secret", algorithm="HS256")


@pytest.mark.asyncio
async def test_unique_uuid(access_token):  # type: ignore[no-untyped-def]
    with TestClient(app) as client:
        first_asset = create_asset(client, access_token)

        with pytest.raises(httpx.HTTPStatusError):
            create_asset(client, access_token, the_uuid=first_asset["uuid"])

        second_asset = create_asset(client, access_token)
        assert first_asset["uuid"] != second_asset["uuid"]


@pytest.mark.asyncio
async def test_auto_uuid(access_token):  # type: ignore[no-untyped-def]
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


@pytest.mark.asyncio
async def test_asset_object_quality_check(access_token):  # type: ignore[no-untyped-def]
    asset_id = upload_test_files(access_token, num_files=4)

    async with with_session() as session:
        stmt = select(UploadedS3Object).where(UploadedS3Object.asset_id == asset_id)
        result = await session.execute(stmt)
        s3objects = result.scalars().all()
        s3obj_ids = [obj.id for obj in s3objects]

        pending = await find_s3object_pending_quality_check(session=session)
        assert not pending or len(pending) == 0

        await update_s3object_quality_check_flag(
            session=session, ids=s3obj_ids[:-1], value=True
        )

        pending = await find_s3object_pending_quality_check(session=session)
        assert len(pending) == (len(s3objects) - 1)

        await update_s3object_quality_check_flag(
            session=session, ids=s3obj_ids[0], value=False
        )

        pending = await find_s3object_pending_quality_check(session=session)
        assert len(pending) == (len(s3objects) - 2)


@pytest.mark.parametrize(
    "access_token",
    [{"is_admin": False}],
    indirect=True,
)
@pytest.mark.asyncio
async def test_asset_object_quality_check_endpoints(access_token):  # type: ignore[no-untyped-def]
    num_files = 4
    asset_id = upload_test_files(access_token, num_files=num_files)

    async with with_session() as session:
        stmt = select(UploadedS3Object).where(UploadedS3Object.asset_id == asset_id)
        result = await session.execute(stmt)
        s3objects = result.scalars().all()
        s3obj_ids = [obj.id for obj in s3objects]

    forbidden_asset_id = upload_test_files(access_token, num_files=2)

    async with with_session() as session:
        stmt = select(Asset).where(Asset.id == forbidden_asset_id)
        result = await session.execute(stmt)
        asset = result.scalars().one()
        asset.username = uuid.uuid4().hex
        session.add(asset)
        await session.commit()
        forbidden_s3obj_ids = [obj.id for obj in asset.objects]

    headers = {"Authorization": f"Bearer {access_token}"}

    with TestClient(app) as client:
        resp_get_before = client.get("/asset/object/quality-check", headers=headers)
        assert resp_get_before.raise_for_status()
        resp_json = resp_get_before.json()
        _logger.info("Response:\n%s", pprint.pformat(resp_json))
        assert len(resp_json) == 0

        num_flagged = 2

        post_body = {
            "asset_object_id": [*s3obj_ids[:num_flagged], *forbidden_s3obj_ids],
            "pending_quality_check": True,
        }

        resp_post = client.post(
            "/asset/object/quality-check", headers=headers, json=post_body
        )

        assert resp_post.raise_for_status()

        resp_get_after = client.get("/asset/object/quality-check", headers=headers)
        assert resp_get_after.raise_for_status()
        resp_json = resp_get_after.json()
        _logger.info("Response:\n%s", pprint.pformat(resp_json))
        assert len(resp_json) == num_flagged
        assert len(post_body["asset_object_id"]) > num_flagged
        assert all(item["asset_id"] != forbidden_asset_id for item in resp_json)


@pytest.mark.asyncio
async def test_public_read_private_asset(access_token):  # type: ignore[no-untyped-def]
    """Public anonymous users should not be able to read private assets."""

    asset_id = upload_test_files(access_token, num_files=random.randint(1, 4))

    async with with_session() as session:
        stmt = select(Asset).where(Asset.id == asset_id)
        result = await session.execute(stmt)
        asset = result.scalars().one()
        assert asset.access_level == AssetAccessLevels.PRIVATE

    with TestClient(app) as client:
        resp_auth = client.get(
            "/asset/public", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert resp_auth.raise_for_status()
        data_auth = resp_auth.json()
        assert len(data_auth) == 1

        resp_public = client.get("/asset/public")
        assert resp_public.raise_for_status()
        data_public = resp_public.json()
        assert len(data_public) == 0


@pytest.mark.asyncio
async def test_basic_user_cannot_manage_another_users_assets():  # type: ignore[no-untyped-def]
    owner_token = _make_access_token("asset-owner")
    other_token = _make_access_token("other-basic-user")

    with TestClient(app) as client:
        public_asset = create_asset(
            client,
            owner_token,
            asset_kwargs={"access_level": AssetAccessLevels.PUBLIC.value},
        )
        visible_asset = create_asset(
            client,
            owner_token,
            asset_kwargs={"access_level": AssetAccessLevels.VISIBLE.value},
        )

    upload_test_files(owner_token, num_files=1, the_asset=public_asset)
    upload_test_files(owner_token, num_files=1, the_asset=visible_asset)

    async with with_session() as session:
        public = await session.get(Asset, public_asset["id"])
        visible = await session.get(Asset, visible_asset["id"])
        assert public and visible
        public_object = public.objects[0]
        visible_object = visible.objects[0]

    with TestClient(app) as client:
        # Basic user can READ public and visible assets
        for asset in [public_asset, visible_asset]:
            resp_get = client.get(
                f"/asset/{asset['id']}",
                headers={"Authorization": f"Bearer {other_token}"},
            )
            assert resp_get.status_code == 200

            # But cannot UPDATE or DELETE
            assert (
                client.patch(
                    f"/asset/{asset['id']}",
                    headers={"Authorization": f"Bearer {other_token}"},
                    json={"name": str(uuid.uuid4())},
                ).status_code
                == 404
            )
            assert (
                client.delete(
                    f"/asset/{asset['id']}",
                    headers={"Authorization": f"Bearer {other_token}"},
                ).status_code
                == 404
            )

        # Batch endpoint returns objects from visible and public assets
        resp_batch = client.get(
            "/asset/object/batch",
            headers={"Authorization": f"Bearer {other_token}"},
            params={"ids": f"{public_object.id},{visible_object.id}"},
        )
        assert resp_batch.raise_for_status()
        batch_ids = {item["id"] for item in resp_batch.json()}
        assert public_object.id in batch_ids
        assert visible_object.id in batch_ids


@pytest.mark.asyncio
async def test_basic_user_catalogue_and_download_access_by_asset_level():  # type: ignore[no-untyped-def]
    owner_token = _make_access_token("asset-owner")
    other_token = _make_access_token("other-basic-user")

    with TestClient(app) as client:
        public_asset = create_asset(
            client,
            owner_token,
            asset_kwargs={"access_level": AssetAccessLevels.PUBLIC.value},
        )
        visible_asset = create_asset(
            client,
            owner_token,
            asset_kwargs={"access_level": AssetAccessLevels.VISIBLE.value},
        )

    upload_test_files(owner_token, num_files=1, the_asset=public_asset)
    upload_test_files(owner_token, num_files=1, the_asset=visible_asset)

    async with with_session() as session:
        public = await session.get(Asset, public_asset["id"])
        visible = await session.get(Asset, visible_asset["id"])
        assert public and visible
        public_object = public.objects[0]
        visible_object = visible.objects[0]

    with TestClient(app) as client:
        resp_catalogue = client.get(
            "/asset/object/batch",
            headers={"Authorization": f"Bearer {other_token}"},
            params={"ids": f"{public_object.id},{visible_object.id}"},
        )
        assert resp_catalogue.raise_for_status()
        catalogue_ids = {item["id"] for item in resp_catalogue.json()}
        assert public_object.id in catalogue_ids
        assert visible_object.id in catalogue_ids

        resp_public_download = client.get(
            f"/asset/{public_asset['id']}/download-urls",
            headers={"Authorization": f"Bearer {other_token}"},
            params={"object_id": public_object.id},
        )
        assert resp_public_download.raise_for_status()

        resp_visible_download = client.get(
            f"/asset/{visible_asset['id']}/download-urls",
            headers={"Authorization": f"Bearer {other_token}"},
            params={"object_id": visible_object.id},
        )
        assert resp_visible_download.status_code == 404


@pytest.mark.asyncio
async def test_basic_user_can_view_public_and_visible_assets_in_catalogue():  # type: ignore[no-untyped-def]
    owner_token = _make_access_token("asset-owner")
    other_token = _make_access_token("other-basic-user")

    with TestClient(app) as client:
        public_asset = create_asset(
            client,
            owner_token,
            asset_kwargs={"access_level": AssetAccessLevels.PUBLIC.value},
        )
        visible_asset = create_asset(
            client,
            owner_token,
            asset_kwargs={"access_level": AssetAccessLevels.VISIBLE.value},
        )
        private_asset = create_asset(
            client,
            owner_token,
            asset_kwargs={"access_level": AssetAccessLevels.PRIVATE.value},
        )

    upload_test_files(owner_token, num_files=1, the_asset=public_asset)
    upload_test_files(owner_token, num_files=1, the_asset=visible_asset)
    upload_test_files(owner_token, num_files=1, the_asset=private_asset)

    with TestClient(app) as client:
        # GET /asset should return public and visible, but not private
        resp_list = client.get(
            "/asset",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp_list.raise_for_status()
        list_ids = {item["id"] for item in resp_list.json()}
        assert public_asset["id"] in list_ids
        assert visible_asset["id"] in list_ids
        assert private_asset["id"] not in list_ids

        # GET /asset/object should return objects from public and visible
        resp_objects = client.get(
            "/asset/object",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp_objects.raise_for_status()
        object_asset_ids = {obj["asset_id"] for obj in resp_objects.json()}
        assert public_asset["id"] in object_asset_ids
        assert visible_asset["id"] in object_asset_ids
        assert private_asset["id"] not in object_asset_ids


@pytest.mark.asyncio
async def test_asset_object_management_requires_owner_and_matching_asset():  # type: ignore[no-untyped-def]
    owner_token = _make_access_token("asset-owner")
    other_token = _make_access_token("other-basic-user")

    owner_asset_id = upload_test_files(owner_token, num_files=1)
    other_asset_id = upload_test_files(other_token, num_files=1)

    async with with_session() as session:
        owner_asset = await session.get(Asset, owner_asset_id)
        other_asset = await session.get(Asset, other_asset_id)
        assert owner_asset and other_asset
        owner_object = owner_asset.objects[0]
        other_object = other_asset.objects[0]

    with TestClient(app) as client:
        assert (
            client.patch(
                f"/asset/{owner_asset_id}/object/{owner_object.id}",
                headers={"Authorization": f"Bearer {other_token}"},
                json={"name": "not allowed"},
            ).status_code
            == 404
        )

        assert (
            client.delete(
                f"/asset/{owner_asset_id}/object/{owner_object.id}",
                headers={"Authorization": f"Bearer {other_token}"},
            ).status_code
            == 404
        )

        assert (
            client.patch(
                f"/asset/{other_asset_id}/object/{owner_object.id}",
                headers={"Authorization": f"Bearer {other_token}"},
                json={"name": "wrong asset"},
            ).status_code
            == 404
        )

        assert (
            client.delete(
                f"/asset/{other_asset_id}/object/{owner_object.id}",
                headers={"Authorization": f"Bearer {other_token}"},
            ).status_code
            == 404
        )

        resp_update_own = client.patch(
            f"/asset/{other_asset_id}/object/{other_object.id}",
            headers={"Authorization": f"Bearer {other_token}"},
            json={"name": "allowed"},
        )
        assert resp_update_own.raise_for_status()


@pytest.mark.asyncio
async def test_basic_user_cannot_create_ownerless_public_asset():  # type: ignore[no-untyped-def]
    basic_token = _make_access_token("basic-user")
    admin_token = _make_access_token("admin-user", is_admin=True)

    payload = {
        "name": str(uuid.uuid4()),
        "is_public_ownerless": True,
    }

    with TestClient(app) as client:
        assert (
            client.post(
                "/asset",
                headers={"Authorization": f"Bearer {basic_token}"},
                json=payload,
            ).status_code
            == 403
        )

        resp_admin = client.post(
            "/asset",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={**payload, "name": str(uuid.uuid4())},
        )
        assert resp_admin.raise_for_status()
        assert resp_admin.json()["username"] is None


@pytest.mark.asyncio
async def test_update_asset_description(access_token):  # type: ignore[no-untyped-def]
    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        asset = create_asset(
            client, access_token, asset_kwargs={"description": "initial description"}
        )
        asset_id = asset["id"]

        new_description = "updated description with DOI: 10.5281/zenodo.123456"
        resp_patch = client.patch(
            f"/asset/{asset_id}",
            headers=headers,
            json={"description": new_description},
        )
        assert resp_patch.raise_for_status()
        assert resp_patch.json()["description"] == new_description

        resp_get = client.get(f"/asset/{asset_id}", headers=headers)
        assert resp_get.raise_for_status()
        assert resp_get.json()["description"] == new_description

        # PATCH without description must not wipe the existing value
        resp_patch_name = client.patch(
            f"/asset/{asset_id}",
            headers=headers,
            json={"name": str(uuid.uuid4())},
        )
        assert resp_patch_name.raise_for_status()
        assert resp_patch_name.json()["description"] == new_description
