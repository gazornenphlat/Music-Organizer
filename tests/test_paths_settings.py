"""Every library location is configurable in Settings, and beets gets its paths from those settings."""

from pathlib import Path

import music_pipeline as mp
import toolkit_core as core
import toolkit_web


def test_template_has_only_tokens_for_beets_paths():
    text = mp.BEETS_CONFIG_TEMPLATE.read_text(encoding="utf-8")
    assert "__BEETS_DIR__" in text
    assert "__BEETS_LIBRARY__" in text
    assert "__BEETS_IMPORT_LOG__" in text
    # No real drive paths left in the template.
    assert "M:/" not in text
    assert "M:\\" not in text


def test_render_fills_every_token(tmp_path):
    rendered = mp.render_beets_config(
        'directory: "__BEETS_DIR__"\nlibrary: "__BEETS_LIBRARY__"\nlog: "__BEETS_IMPORT_LOG__"\n',
        {"BEETS_DIR": tmp_path / "beets", "BEETS_LIBRARY": tmp_path / "lib.db",
         "BEETS_IMPORT_LOG": tmp_path / "beets" / "import.log"})
    assert "__BEETS" not in rendered
    # beets expects forward slashes, even on Windows
    assert str(tmp_path / "lib.db").replace("\\", "/") in rendered
    assert "\\" not in rendered


def test_write_runtime_config_uses_settings_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "BEETS_RUNTIME_CONFIG", tmp_path / "runtime.yaml")
    out = mp.write_beets_runtime_config(tmp_path / "b", tmp_path / "x.db", tmp_path / "b" / "log.txt")
    text = out.read_text(encoding="utf-8")
    assert (tmp_path / "b").as_posix() in text
    for token in ("__BEETS_DIR__", "__BEETS_LIBRARY__", "__BEETS_IMPORT_LOG__"):
        assert token not in text


def test_defaults_come_from_one_library_root():
    # The only drive literal is LIBRARY_ROOT; every default folder derives from it.
    assert str(mp.COMPLETE_DIR).startswith(str(mp.LIBRARY_ROOT))
    assert str(mp.BEETS_DIR).startswith(str(mp.LIBRARY_ROOT))
    source = Path(mp.__file__).read_text(encoding="utf-8")
    assert source.count('"M:') + source.count("'M:") <= 1


def test_every_path_setting_has_a_default_key():
    for attr, _label, key, kind in core.ALL_PATH_SETTINGS:
        assert key in core.PIPELINE_DEFAULT_PATHS
        assert kind in ("dir", "file")
        assert key in core.default_settings()


def test_apply_paths_overrides_beets_paths_and_restores(tmp_path):
    original = mp.BEETS_LIBRARY
    try:
        core.apply_paths_from({"path_beets_library": str(tmp_path / "custom.db"),
                               "path_beets_dir": str(tmp_path / "bd")})
        assert mp.BEETS_LIBRARY == tmp_path / "custom.db"
        assert mp.BEETS_DIR == tmp_path / "bd"
    finally:
        core.apply_paths_from(core.PIPELINE_DEFAULT_PATHS)
        assert mp.BEETS_LIBRARY == original


def test_web_settings_report_path_kinds():
    client = toolkit_web.app.test_client()
    data = client.get("/api/settings").get_json()
    kinds = {p["key"]: p["kind"] for p in data["path_settings"]}
    assert kinds["path_beets_dir"] == "dir"
    assert kinds["path_beets_library"] == "file"
    assert kinds["path_pipeline_log"] == "file"
    assert kinds["path_complete"] == "dir"


def test_discogs_token_goes_into_beets_config_and_empty_stays_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "BEETS_RUNTIME_CONFIG", tmp_path / "runtime.yaml")
    out = mp.write_beets_runtime_config(tmp_path / "b", tmp_path / "x.db", tmp_path / "b" / "log.txt",
                                        'abc"def')
    text = out.read_text(encoding="utf-8")
    assert 'user_token: "abcdef"' in text          # quotes stripped so the YAML stays valid
    out = mp.write_beets_runtime_config(tmp_path / "b", tmp_path / "x.db", tmp_path / "b" / "log.txt", "")
    assert 'user_token: ""' in out.read_text(encoding="utf-8")


def test_discogs_token_is_never_returned_by_web_settings(monkeypatch):
    monkeypatch.setitem(toolkit_web.SETTINGS, "discogs_token", "secret-token")
    client = toolkit_web.app.test_client()
    data = client.get("/api/settings").get_json()
    assert "discogs_token" not in data["settings"]
    assert data["settings"]["discogs_token_set"] is True
    assert "secret-token" not in str(data)


def test_blank_discogs_token_keeps_saved_one(monkeypatch):
    monkeypatch.setitem(toolkit_web.SETTINGS, "discogs_token", "kept")
    monkeypatch.setattr(core, "save_settings", lambda data: None)   # don't touch the real settings file
    toolkit_web.settings_update({"discogs_token": ""})
    assert toolkit_web.SETTINGS["discogs_token"] == "kept"
