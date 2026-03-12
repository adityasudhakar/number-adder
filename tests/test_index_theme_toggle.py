from pathlib import Path


def test_index_includes_theme_toggle_and_persistence_script():
    index_path = Path(__file__).resolve().parents[1] / "number_adder" / "static" / "index.html"
    body = index_path.read_text(encoding="utf-8")
    assert 'id="theme-toggle"' in body
    assert "localStorage.getItem('theme')" in body
    assert "localStorage.setItem(THEME_KEY, nextTheme)" in body
    assert 'data-theme' in body
