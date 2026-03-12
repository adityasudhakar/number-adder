from fastapi.testclient import TestClient

from number_adder.server import app


def test_index_includes_footer_version_loader():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="app-version"' in response.text
    assert "fetch('/version')" in response.text
    assert "version unavailable" in response.text
