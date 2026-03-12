from fastapi.testclient import TestClient

from number_adder.server import app


def test_version_ok():
    client = TestClient(app)
    r = client.get("/version")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "git_sha" in data
