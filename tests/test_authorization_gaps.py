"""Regression tests for role and permission enforcement.

These tests pin down behavior that is easy to break with a small refactor:

  - ``GET /asset/validation/supported-extensions`` requires a valid token.
  - A DID creation task created on behalf of a target user is owned by
    that user (so the target can poll their own task).
  - The admin bypass in ``User.enforce_raise`` short-circuits the static
    Casbin policy, including explicit ``deny`` rules.
"""

import logging
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from moderate_api.db import with_session
from moderate_api.entities.user.models import UserMeta
from moderate_api.long_running import init_task
from moderate_api.main import app

_logger = logging.getLogger(__name__)


def _make_token(username: str, *, is_admin: bool = False) -> str:
    roles = ["api_basic_access"]
    if is_admin:
        roles.append("api_admin")
    payload = {
        "preferred_username": username,
        "resource_access": {"apisix": {"roles": roles}},
        "realm_access": {"roles": []},
        "exp": 9999999999,
        "iat": 0,
    }
    return jwt.encode(payload, "secret", algorithm="HS256")


@pytest.mark.asyncio
async def test_supported_extensions_requires_auth():
    """Anonymous callers must not be able to read supported extensions."""
    with TestClient(app) as client:
        response = client.get("/asset/validation/supported-extensions")
        assert response.status_code == 401, (
            f"Expected 401 without Authorization header. "
            f"Got {response.status_code}: {response.text!r}"
        )


@pytest.mark.asyncio
async def test_did_task_owned_by_target_user_visible_to_target():
    """A DID task created on behalf of a target user must be owned by that
    user, so the target can poll it via ``GET /user/did/task/{id}``.

    The POST handler in ``moderate_api/entities/user/router.py`` calls
    ``init_task(username_owner=body.username)``. This test seeds the
    resulting ownership state directly (rather than driving the POST
    endpoint, which requires a live Trust Service) and asserts the GET
    endpoint serves the target user correctly while keeping unrelated
    users out.
    """
    target_username = f"target-{uuid.uuid4()}"
    other_username = f"other-{uuid.uuid4()}"

    with TestClient(app) as client:
        async with with_session() as session:
            task_id = await init_task(
                session=session, username_owner=target_username
            )
            await session.commit()

        target_token = _make_token(target_username)
        response = client.get(
            f"/user/did/task/{task_id}",
            headers={"Authorization": f"Bearer {target_token}"},
        )
        assert response.status_code == 200, (
            "Target user must see the DID task created on their behalf. "
            f"Got {response.status_code}: {response.text!r}"
        )

        other_token = _make_token(other_username)
        other_response = client.get(
            f"/user/did/task/{task_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert other_response.status_code == 404, other_response.text


@pytest.mark.asyncio
async def test_admin_bypass_overrides_deny_user_delete():
    """The admin bypass in ``User.enforce_raise`` short-circuits Casbin,
    so the explicit ``user.delete = deny`` rule in the static policy does
    not apply to admins. This pins down current semantics; a future
    change that drops the bypass would surface here.
    """
    admin_username = f"admin-{uuid.uuid4()}"
    target_username = f"target-{uuid.uuid4()}"
    admin_token = _make_token(admin_username, is_admin=True)

    with TestClient(app) as client:
        async with with_session() as session:
            user_meta = UserMeta(username=target_username)
            session.add(user_meta)
            await session.commit()
            await session.refresh(user_meta)
            user_meta_id = user_meta.id

        response = client.delete(
            f"/user/{user_meta_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code in (200, 204), (
            "Admin bypass should override the Casbin 'user.delete=deny' "
            f"policy. Got {response.status_code}: {response.text!r}"
        )
