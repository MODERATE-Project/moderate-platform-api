import logging
import os
import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from moderate_api.main import app

_DISABLE_AUTH_VERIFICATION = "MODERATE_API_DISABLE_TOKEN_VERIFICATION"
_API_GW_CLIENT_ID = "MODERATE_API_OAUTH_NAMES__API_GW_CLIENT_ID"
_ROLE_BASIC_ACCESS = "MODERATE_API_OAUTH_NAMES__ROLE_BASIC_ACCESS"
_LOG_LEVEL = "LOG_LEVEL"

_ENV_KEYS = [
    _DISABLE_AUTH_VERIFICATION,
    _API_GW_CLIENT_ID,
    _ROLE_BASIC_ACCESS,
    _LOG_LEVEL,
]

_original_env = {}

_test_env = {
    _DISABLE_AUTH_VERIFICATION: "true",
    _API_GW_CLIENT_ID: "apisix",
    _ROLE_BASIC_ACCESS: "api_basic_access",
    _LOG_LEVEL: "DEBUG",
}

_logger = logging.getLogger(__name__)


def pytest_configure():
    """Set the environment variables for the tests."""

    _logger.debug("Setting environment variables for tests")

    for key in _ENV_KEYS:
        _original_env[key] = os.environ.get(key, None)

    for key in _ENV_KEYS:
        os.environ[key] = _test_env.get(key)


def pytest_unconfigure():
    """Restore the original environment variables."""

    _logger.debug("Restoring original environment variables")

    for key in _ENV_KEYS:
        if _original_env.get(key) is None:
            os.environ.pop(key)
        else:
            os.environ[key] = _original_env.get(key)


@pytest.fixture
def access_token(request):
    now = int(time.time())

    try:
        access_enabled = request.param.get("access_enabled", True)
    except AttributeError:
        access_enabled = True

    basic_access_role = (
        _test_env[_ROLE_BASIC_ACCESS] if access_enabled else uuid.uuid4().hex
    )

    token_dict = {
        "exp": now + 3600,
        "iat": now - 5,
        "jti": "a793d0a0-badf-489f-a5a0-86719d0c9dff",
        "iss": "http://keycloak:8080/realms/moderate",
        "aud": "account",
        "sub": "38379d51-5a01-4d24-a2ff-f11c90baea20",
        "typ": "Bearer",
        "azp": "apisix",
        "session_state": "dd6aa81b-3df6-4050-8583-cfacc9a1e994",
        "acr": "1",
        "realm_access": {
            "roles": [
                "offline_access",
                "uma_authorization",
                "default-roles-moderate",
                "account:manage-account",
                "account:manage-account-links",
                "account:view-profile",
            ]
        },
        "resource_access": {
            _test_env[_API_GW_CLIENT_ID]: {"roles": [basic_access_role]},
            "account": {
                "roles": ["manage-account", "manage-account-links", "view-profile"]
            },
        },
        "scope": "profile email",
        "sid": "dd6aa81b-3df6-4050-8583-cfacc9a1e994",
        "email_verified": True,
        "name": "Andrés García Mangas",
        "preferred_username": "andres.garcia",
        "given_name": "Andrés",
        "family_name": "García Mangas",
        "email": "andres.garcia@fundacionctic.org",
    }

    encoded_token = jwt.encode(token_dict, "secret", algorithm="HS256")

    yield encoded_token


@pytest.fixture()
def client():
    yield TestClient(app=app)
