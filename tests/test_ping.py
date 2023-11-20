import logging
import pprint

import pytest

_logger = logging.getLogger(__name__)


def test_ping(client, access_token):
    """Test the ping endpoint with authentication."""

    response = client.get("/ping", headers={"Authorization": f"Bearer {access_token}"})
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
def test_ping_invalid_access_token(client, access_token):
    """Test the ping endpoint with an unauthorized user."""

    response = client.get("/ping", headers={"Authorization": f"Bearer {access_token}"})
    assert response.raise_for_status()
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert resp_json.get("user", None) is None


def test_ping_no_access_token(client):
    """Test the ping endpoint without an access token."""

    response = client.get("/ping")
    assert response.raise_for_status()
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert resp_json.get("user", None) is None
