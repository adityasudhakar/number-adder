from fastapi.testclient import TestClient

from number_adder.server import app


FAVICON_TAG = '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml" />'
HTML_PAGES = [
    "/",
    "/api-docs",
    "/docs.html",
    "/dashboard.html",
    "/pricing.html",
    "/privacy.html",
    "/settings.html",
    "/success.html",
    "/cancel.html",
]


def test_favicon_asset_is_served():
    client = TestClient(app)
    response = client.get("/assets/favicon.svg")
    assert response.status_code == 200
    assert "svg" in response.headers.get("content-type", "").lower()
    assert "<svg" in response.text


def test_static_pages_include_favicon_link():
    client = TestClient(app)

    for path in HTML_PAGES:
        response = client.get(path)
        assert response.status_code == 200, path
        assert FAVICON_TAG in response.text, path
