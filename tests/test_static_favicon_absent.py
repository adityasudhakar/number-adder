from pathlib import Path


STATIC_DIR = Path("number_adder/static")
STATIC_HTML_PAGES = [
    "index.html",
    "api-docs.html",
    "docs.html",
    "dashboard.html",
    "pricing.html",
    "privacy.html",
    "settings.html",
    "success.html",
    "cancel.html",
]
FAVICON_MARKERS = [
    'rel="icon"',
    "rel='icon'",
    "shortcut icon",
    "apple-touch-icon",
]
FAVICON_ASSET_GLOBS = [
    "**/favicon.*",
    "**/*favicon*.ico",
    "**/*apple-touch-icon*",
]


def test_static_pages_do_not_declare_favicons():
    for html_name in STATIC_HTML_PAGES:
        content = (STATIC_DIR / html_name).read_text(encoding="utf-8").lower()
        for marker in FAVICON_MARKERS:
            assert marker not in content, f"{html_name} contains favicon marker: {marker}"


def test_no_favicon_assets_in_static_tree():
    matches = set()
    for pattern in FAVICON_ASSET_GLOBS:
        matches.update(STATIC_DIR.glob(pattern))
    assert not matches, f"Unexpected favicon assets found: {sorted(str(p) for p in matches)}"
