from pathlib import Path
import re


STATIC_DIR = Path(__file__).resolve().parents[1] / "number_adder" / "static"

# Catch common favicon declarations in <link> tags.
FAVICON_PATTERNS = [
    re.compile(r"<link[^>]*rel\s*=\s*['\"]?icon['\"]?", re.IGNORECASE),
    re.compile(r"<link[^>]*rel\s*=\s*['\"]?shortcut\s+icon['\"]?", re.IGNORECASE),
    re.compile(r"<link[^>]*rel\s*=\s*['\"]?apple-touch-icon['\"]?", re.IGNORECASE),
    re.compile(r"<link[^>]*href\s*=\s*['\"][^'\"]*favicon[^'\"]*['\"]", re.IGNORECASE),
]


def test_static_pages_do_not_declare_favicon_links():
    html_files = sorted(STATIC_DIR.glob("*.html"))
    assert html_files, "Expected static HTML pages to exist"

    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8")
        for pattern in FAVICON_PATTERNS:
            assert pattern.search(content) is None, (
                f"Found favicon-related markup in {html_file.name}: {pattern.pattern}"
            )
