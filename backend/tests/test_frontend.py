def test_react_pages_get_index_html(client, settings, tmp_path):
    (tmp_path / "index.html").write_text("<div id='root'></div>")
    settings.FRONTEND_DIST = tmp_path
    for url in ("/", "/projects/12", "/p/some-token"):
        response = client.get(url)
        assert response.status_code == 200
        assert b"id='root'" in response.content


def test_api_paths_are_not_sent_to_react(client, settings, tmp_path):
    settings.FRONTEND_DIST = tmp_path  # no build
    assert client.get("/").status_code == 404
    assert client.get("/api/health").json() == {"status": "ok"}
