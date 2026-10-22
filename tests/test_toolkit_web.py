from __future__ import annotations

import toolkit_web


def test_open_api_rejects_files(tmp_path, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(toolkit_web.os, "startfile", lambda path: calls.append(path), raising=False)

    target = tmp_path / "payload.exe"
    target.write_bytes(b"not really an executable")

    response = toolkit_web.app.test_client().post("/api/open", json={"path": str(target)})

    assert response.status_code == 400
    assert calls == []


def test_open_api_still_opens_folders(tmp_path, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(toolkit_web.sys, "platform", "win32")
    monkeypatch.setattr(toolkit_web.os, "startfile", lambda path: calls.append(path), raising=False)

    target = tmp_path / "album"
    target.mkdir()

    response = toolkit_web.app.test_client().post("/api/open", json={"path": str(target)})

    assert response.status_code == 200
    assert calls == [str(target)]


# ---------------------------------------------------------------- smoke tests

def test_web_app_state_endpoint():
    client = toolkit_web.app.test_client()
    response = client.get("/api/state")

    assert response.status_code == 200
    data = response.get_json()
    assert "jobs" in data
    assert "pipeline" in data
    assert set(data["jobs"]) == {"pipeline", "dupes", "health", "review", "plex"}


def test_web_app_settings_endpoint():
    client = toolkit_web.app.test_client()
    response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.get_json()
    assert "settings" in data
    assert "capabilities" in data


def test_web_app_index_page():
    client = toolkit_web.app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"Music Toolkit" in response.data


def test_pipeline_preflight_rejects_missing_folder(tmp_path):
    client = toolkit_web.app.test_client()
    response = client.post("/api/pipeline/preflight", json={"pipe_folder": str(tmp_path / "does-not-exist")})

    assert response.status_code == 200
    assert response.get_json()["errors"]
