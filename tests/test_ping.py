import logging
import pprint

import pytest

_logger = logging.getLogger(__name__)


def test_ping_no_auth(client):
    """Test the ping endpoint without authentication."""

    response = client.get("/ping")
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert response.status_code == 200
    assert resp_json["datetime"]
    assert resp_json["python_version"]
    assert resp_json.get("user", None) is None


def test_ping_auth(client, access_token):
    """Test the ping endpoint with authentication."""

    response = client.get(
        "/ping/auth", headers={"Authorization": f"Bearer {access_token}"}
    )

    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert response.status_code == 200
    assert resp_json["datetime"]
    assert resp_json["python_version"]
    assert resp_json["user"]


@pytest.mark.parametrize(
    "access_token",
    [{"access_enabled": False}],
    indirect=True,
)
def test_ping_auth_basic_access_disabled(client, access_token):
    """Test the ping endpoint with authentication and basic access disabled."""

    response = client.get(
        "/ping/auth", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 401
