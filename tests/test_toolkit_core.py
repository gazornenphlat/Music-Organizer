from __future__ import annotations

import threading
from pathlib import Path

import toolkit_core as core


def test_remove_path_deletes_a_file(tmp_path):
    target = tmp_path / "track.flac"
    target.write_bytes(b"audio")

    core.remove_path(target, use_trash=False)

    assert not target.exists()


def test_remove_path_deletes_a_directory_tree(tmp_path):
    target = tmp_path / "album" / "Scans"
    target.mkdir(parents=True)
    (target / "cover.jpg").write_bytes(b"artwork")

    core.remove_path(tmp_path / "album", use_trash=False)

    assert not (tmp_path / "album").exists()


def test_remove_path_uses_the_recycle_bin_when_available(tmp_path, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(core, "send2trash", lambda path: calls.append(path))

    target = tmp_path / "track.flac"
    target.write_bytes(b"audio")
    core.remove_path(target, use_trash=True)

    assert calls == [str(target)]
    assert target.exists()          # the fake "trash" did not really delete it


def test_remove_path_refuses_trash_without_send2trash(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setattr(core, "send2trash", None)
    target = tmp_path / "track.flac"
    target.write_bytes(b"audio")

    with pytest.raises(RuntimeError):
        core.remove_path(target, use_trash=True)
    assert target.exists()


def test_run_pipeline_reports_a_busy_lock_instead_of_starting(tmp_path, monkeypatch):
    import threading

    lock_path = tmp_path / "pipeline.lock"
    original = core.mp.PipelineLock
    factory = lambda *a, **k: original(lock_path)  # noqa: E731
    monkeypatch.setattr(core.mp, "PipelineLock", factory)

    holder = factory()
    holder.acquire()
    events: list[tuple[str, tuple]] = []

    class Bus:
        def post(self, kind, *payload):
            events.append((kind, payload))

    history = core.History(core.Value(str(tmp_path)), core.Value(False))
    try:
        err = core.run_pipeline(
            tmp_path,
            {"convert": False, "cleanup": False, "dry_run": True},
            Bus(), history, threading.Event(), lambda _folder: "c",
        )
    finally:
        holder.release()

    assert err and "already running" in err
    assert events[-1][0] == "pipeline_done"


def test_review_recheck_finds_nested_multi_disc_incomplete_folder(tmp_path, monkeypatch):
    incomplete = tmp_path / "incomplete"
    album = incomplete / "Album"
    (album / "CD1").mkdir(parents=True)
    (album / "CD1" / "01.flac").write_bytes(b"audio")

    seen: list[Path] = []

    def fake_scan(folder):
        seen.append(folder)
        return {"artist": "Artist", "album": "Album", "mbid": None, "titles": ["Track"],
                "discs": {1: {"tracks": {1}, "expected_total": 1}}}

    monkeypatch.setattr(core.mp, "INCOMPLETE_DIR", incomplete)
    monkeypatch.setattr(core.mp, "scan_folder", fake_scan)
    monkeypatch.setattr(core.mp, "find_release", lambda *a, **k: {
        "result": None, "release": None, "candidates": [], "how": "no match"})
    monkeypatch.setattr(core.mp, "save_unmatched", lambda *a, **k: None)
    monkeypatch.setattr(core.mp, "save_cache", lambda *a, **k: None)

    entries: dict = {}
    found = core.review_recheck(entries, True, threading.Event(), lambda *a: None)

    assert str(album) in entries
    assert seen == [album]
    assert found == 0


def test_review_move_tags_and_moves_nested_disc_folders(tmp_path, monkeypatch):
    incomplete = tmp_path / "incomplete"
    album = incomplete / "Album"
    first = album / "CD1" / "01.flac"
    second = album / "CD2" / "02.flac"
    first.parent.mkdir(parents=True)
    second.parent.mkdir()
    first.write_bytes(b"audio")
    second.write_bytes(b"audio")

    complete = tmp_path / "complete"
    tagged: list[Path] = []
    monkeypatch.setattr(core.mp, "COMPLETE_DIR", complete)
    monkeypatch.setattr(core.mp, "unique_dest", lambda path: path)
    monkeypatch.setattr(core.mp, "write_album_id", lambda path, mbid: tagged.append(path))
    monkeypatch.setattr(core.mp, "save_unmatched", lambda *a, **k: None)

    class History:
        def write(self, *args):
            pass

    entries = {str(album): {"folder": str(album),
                            "match": {"id": "mbid", "artist": "Artist", "title": "Album"}}}

    moved = core.review_move(entries, [str(album)], True, History(),
                             threading.Event(), lambda *a: None)

    assert moved == 1
    assert entries == {}
    assert not album.exists()
    assert set(tagged) == {first, second}
    assert (complete / "Artist - Album" / "CD1" / "01.flac").exists()
    assert (complete / "Artist - Album" / "CD2" / "02.flac").exists()
