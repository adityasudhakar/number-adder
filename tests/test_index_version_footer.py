def test_index_footer_includes_version_target_and_client_fetch():
    html = open("number_adder/static/index.html", "r", encoding="utf-8").read()

    assert 'id="app-version"' in html
    assert "fetch('/version')" in html
