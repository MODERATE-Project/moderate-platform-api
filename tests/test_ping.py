import logging
import pprint

from fastapi.testclient import TestClient

from moderate_api.main import app

_logger = logging.getLogger(__name__)


def test_ping_no_auth():
    """Test the ping endpoint without authentication."""

    client = TestClient(app)
    response = client.get("/ping")
    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert response.status_code == 200
    assert resp_json["datetime"]
    assert resp_json["python_version"]
    assert resp_json.get("user", None) is None


def test_ping_auth(access_token):
    """Test the ping endpoint with authentication."""

    client = TestClient(app)

    response = client.get(
        "/ping/auth", headers={"Authorization": f"Bearer {access_token}"}
    )

    resp_json = response.json()
    _logger.debug("Response:\n%s", pprint.pformat(resp_json))
    assert response.status_code == 200
    assert resp_json["datetime"]
    assert resp_json["python_version"]
    assert resp_json["user"]
