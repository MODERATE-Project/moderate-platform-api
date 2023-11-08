from fastapi.testclient import TestClient

from moderate_api.main import app

client = TestClient(app)


def test_ping_no_auth():
    response = client.get("/ping")
    assert response.status_code == 200
    resp_json = response.json()
    assert resp_json["datetime"]
    assert resp_json["python_version"]
    assert resp_json.get("user", None) is None
