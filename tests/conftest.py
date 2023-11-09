import os
import time

import jwt
import pytest

_DISABLE_AUTH_VERIFICATION = "MODERATE_API_DISABLE_TOKEN_VERIFICATION"
_original_disable_auth_verification = None


def pytest_configure():
    """Disable token verification for the tests."""

    global _original_disable_auth_verification
    _original_disable_auth_verification = os.environ.get(_DISABLE_AUTH_VERIFICATION)
    os.environ[_DISABLE_AUTH_VERIFICATION] = "true"


def pytest_unconfigure():
    """Restore the original value of the token verification flag."""

    global _original_disable_auth_verification
    if _original_disable_auth_verification is None:
        os.environ.pop(_DISABLE_AUTH_VERIFICATION)
    else:
        os.environ[_DISABLE_AUTH_VERIFICATION] = _original_disable_auth_verification


@pytest.fixture
def access_token():
    now = int(time.time())

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
                "apisix:test_apisix_role",
                "account:manage-account",
                "account:manage-account-links",
                "account:view-profile",
            ]
        },
        "resource_access": {
            "apisix": {"roles": ["test_apisix_role"]},
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
