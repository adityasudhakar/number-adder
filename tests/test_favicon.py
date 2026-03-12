from fastapi.testclient import TestClient
from pathlib import Path

from number_adder.server import app


FAVICON_MARKERS = [
    'rel="icon"',
    "shortcut icon",
    "favicon",
]
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


def test_favicon_asset_removed():
    favicon_path = Path(__file__).resolve().parents[1] / "number_adder" / "static" / "assets" / "favicon.svg"
    assert not favicon_path.exists()


def test_static_pages_do_not_include_favicon_link():
    client = TestClient(app)

    for path in HTML_PAGES:
        response = client.get(path)
        assert response.status_code == 200, path
        page_html = response.text.lower()
        for marker in FAVICON_MARKERS:
            assert marker not in page_html, path
