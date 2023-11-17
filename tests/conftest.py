import logging
import os
import time
import uuid

import jwt
import pytest
import pytest_asyncio
import sqlalchemy
from fastapi.testclient import TestClient

from moderate_api.config import get_settings
from moderate_api.db import DBEngine
from moderate_api.main import app
from moderate_api.object_storage import with_s3
from tests.db import DB_SKIP_REASON, ENV_TESTS_POSTGRES_URL, is_db_online_async

_ENV_POSTGRES_URL = "MODERATE_API_POSTGRES_URL"
_ENV_DISABLE_AUTH_VERIFICATION = "MODERATE_API_DISABLE_TOKEN_VERIFICATION"
_ENV_API_GW_CLIENT_ID = "MODERATE_API_OAUTH_NAMES__API_GW_CLIENT_ID"
_ENV_ROLE_BASIC_ACCESS = "MODERATE_API_OAUTH_NAMES__ROLE_BASIC_ACCESS"
_ENV_LOG_LEVEL = "LOG_LEVEL"
_ENV_S3_ACCESS_KEY = "MODERATE_API_S3__ACCESS_KEY"
_ENV_S3_SECRET_KEY = "MODERATE_API_S3__SECRET_KEY"
_ENV_S3_ENDPOINT_URL = "MODERATE_API_S3__ENDPOINT_URL"
_ENV_S3_USE_SSL = "MODERATE_API_S3__USE_SSL"
_ENV_S3_REGION = "MODERATE_API_S3__REGION"
_ENV_S3_BUCKET = "MODERATE_API_S3__BUCKET"

_ENV_KEYS = [
    _ENV_DISABLE_AUTH_VERIFICATION,
    _ENV_API_GW_CLIENT_ID,
    _ENV_ROLE_BASIC_ACCESS,
    _ENV_LOG_LEVEL,
    _ENV_POSTGRES_URL,
    _ENV_S3_ACCESS_KEY,
    _ENV_S3_SECRET_KEY,
    _ENV_S3_ENDPOINT_URL,
    _ENV_S3_USE_SSL,
    _ENV_S3_REGION,
    _ENV_S3_BUCKET,
]


_original_env = {}

_test_env = {
    _ENV_DISABLE_AUTH_VERIFICATION: "true",
    _ENV_API_GW_CLIENT_ID: "apisix",
    _ENV_ROLE_BASIC_ACCESS: "api_basic_access",
    _ENV_LOG_LEVEL: "DEBUG",
    _ENV_POSTGRES_URL: os.getenv(
        ENV_TESTS_POSTGRES_URL,
        "postgresql://postgres:postgres@localhost:5432/testsmoderateapi",
    ),
    _ENV_S3_ACCESS_KEY: os.getenv("TESTS_MINIO_ROOT_USER", "minio"),
    _ENV_S3_SECRET_KEY: os.getenv("TESTS_MINIO_ROOT_PASSWORD", "minio123"),
    _ENV_S3_ENDPOINT_URL: os.getenv(
        "TESTS_MINIO_ENDPOINT_URL", "http://localhost:9000"
    ),
    _ENV_S3_USE_SSL: os.getenv("TESTS_MINIO_USE_SSL", "false"),
    _ENV_S3_REGION: os.getenv("TESTS_MINIO_REGION", "eu-central-1"),
    _ENV_S3_BUCKET: os.getenv("TESTS_MINIO_BUCKET", "moderatetests"),
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
        _test_env[_ENV_ROLE_BASIC_ACCESS] if access_enabled else uuid.uuid4().hex
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
            _test_env[_ENV_API_GW_CLIENT_ID]: {"roles": [basic_access_role]},
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


@pytest_asyncio.fixture(autouse=True, scope="function")
async def drop_all_tables():
    try:
        yield
    finally:
        async with DBEngine.instance().begin() as conn:
            metadata = sqlalchemy.MetaData()
            await conn.run_sync(lambda sc: metadata.reflect(sc))
            await conn.run_sync(lambda sc: metadata.drop_all(sc))
            _logger.info("Dropped all tables")


@pytest_asyncio.fixture(autouse=True, scope="function")
async def skip_if_db_offline():
    _logger.debug("Checking that database is online")

    if await is_db_online_async() is False:
        pytest.skip(DB_SKIP_REASON)


@pytest_asyncio.fixture(scope="function")
async def s3():
    _logger.debug("Checking that S3 is online")

    try:
        settings = get_settings()
        _logger.info("S3 settings:\n%s", settings.s3.json(indent=2))

        async with with_s3(settings=settings) as s3:
            yield s3
    except Exception as ex:
        _logger.info("S3 is offline", exc_info=True)
        pytest.skip("S3 is offline")
