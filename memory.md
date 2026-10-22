# Music Organizer — Project Memory

## Overview
Local music/media library toolkit with three front ends sharing one engine:
- `music_pipeline.py` — engine + CLI (FLAC→M4A conversion, cleanup/sort, MusicBrainz matching)
- `toolkit_core.py` — UI-free shared logic (used by both UIs)
- `music_toolkit.py` — desktop Tkinter app
- `toolkit_web.py` — Flask web app + `web/` (HTML/CSS/JS)

No git repo. Working dir: `C:\Users\Bobu\Downloads\Music Organizer`.

## Key paths / constants
- Default output dirs (hardcoded in `music_pipeline.py`, overridable via settings): `M:\TO SORT\AAA_CUE`, `M:\sort_script\aaa_complete`, `aaa_incomplete`, `aaa_delete`.
- Settings file: `music_toolkit_settings.json` (next to scripts). History logs: `history/history_YYYY-MM-DD.log`.
- Caches: `mb_cache_v3.json`, `mb_manual_matches.json`, `mb_unmatched.json`.
- Pipeline lock: `music_pipeline.lock` (cross-process via msvcrt/fcntl + in-process threading.Lock).
- Protected dirs = the four output dirs (source must not be inside them).

## Safety model
- `DRY_RUN` global; `act(desc, fn, *a, **kw)` prints instead of running when dry.
- `remove_path(p, use_trash)` raises if trash requested but `send2trash` missing (no silent permanent delete).
- `remove_empty_folders` only removes genuinely empty dirs (preserves WAV/OGG/APE, Scans/, artwork, .cue, notes).
- Converted FLAC originals, duplicate deletes, Plex cleanup route through `act()`/`remove_path()` so Recycle Bin + history apply.
- `PipelineLock` prevents concurrent pipeline runs across CLI/desktop/web.

## MusicBrainz matching ladder (stage 2)
1. Manual matches (`mb_manual_matches.json`)
2. MBID already in tags
3. Album search (tags as-is, then noise-stripped); first release whose disc+track counts fit wins
4. Track-title search (2-3 shared titles)
5. Suspected missing disc: if a release covers all folder discs plus more (folder holds ≥2 discs), route to Incomplete/Review instead of trusting tags.

## Multi-disc grouping
- `iter_album_groups()` groups sibling folders sharing artist+album tags where each has a distinct single disc number.
- `process_folder(folder, music_files, stats, tagged=..., sources=...)` handles one or many source folders; multi-disc keeps `CD1`/`CD2` subfolders in destination.
- `scan_folder()` is recursive (for Review tab multi-disc support).
- Review re-check/move and desktop Plex scan were consolidated into `toolkit_core` helpers.

## Web design
Current theme: "Ember Pill Mobile" (light). Files: `web/style.css`, `web/index.html`.
- Palette: bg #FFFFFF, surface #FFFFFF, surface-alt #F2F2F7, on-surface #000000, muted #6C6C70, border #E5E5EA, primary #F37F46, success #34C759, error #FF3B30, warning #FF9500, accent-blue #007AFF, accent-indigo #5856D6, accent-yellow #F5C842.
- Font: Nunito Sans (Google Fonts). Icons: Solar bold (bundled in `web/icons.js`).
- Shape language: pills for actions/nav, 28-32px cards, 14px chips, floating glass tab capsule.

## Desktop theme
`music_toolkit.py` `T` dict uses the same Ember palette. Fonts: bundled Manrope + Space Grotesk (Nunito not bundled → fallback).

## Testing
- `pytest.ini`: `testpaths = tests`. `tests/conftest.py` stubs `musicbrainzngs`, `tqdm`, `mutagen` if missing.
- Run: `python -m pytest -q` → **50 passed**.
- Test files: `test_music_pipeline.py`, `test_toolkit_core.py`, `test_toolkit_web.py`.
- Optional deps in dev: `requirements-dev.txt` (core + pytest + flask).

## Dependencies
- Core: `tqdm`, `mutagen`, `musicbrainzngs` (requirements.txt).
- Optional: `send2trash`, `plexapi`, `pyacoustid`, `flask` (requirements-optional.txt).
- External binaries: `ffmpeg`/`ffprobe` (required), `beets` (optional), `fpcalc` (optional, for fingerprints).

## Recent changes (summary)
- Multi-disc album grouping + recursive scan_folder + review helpers.
- `/api/open` restricted to directories (400 for files).
- `remove_path` + Plex trash-aware delete (skips API delete when trashing mapped local file, then refreshes library).
- FLAC originals routed through `act()` (Recycle Bin/history/dry-run).
- `PipelineLock`/`PipelineBusy` cross-process.
- `remove_non_music_folders` → alias to safe `remove_empty_folders`.
- Missing-disc detection in `find_release`.
- Dry-run no longer prompts for single-FLAC folders.
- Stale `.partial.m4a` sweep at conversion start.
- Duplicate tag scan parallelized; web review read/write race fixed.
- CLI `--contact`, `--bitrate`, `--version` flags.
- Desktop settings reset uses `PIPELINE_DEFAULT_PATHS`.
- Consolidated Review/Plex scan+apply into `toolkit_core` (web + desktop both delegate).
- Checkbox visibility fixed in both UIs.
- Restyled both UIs to Ember Pill Mobile.

## Known limitations
- Output paths default to `M:\...`; set before first run.
- `MB_CONTACT` placeholder in `music_pipeline.py`.
- Flask dev server; use waitress for LAN production.
- Web access token carried in URL.
- Only pipeline is locked; other jobs can overlap across front ends.
- Multi-disc grouping requires distinct disc tags (conservative fallback otherwise).
- Desktop uses Manrope/Space Grotesk (Nunito not bundled).
- No git repo.

---

# Music Organizer — Session Work Log (memory2)

This file documents the changes made in this session, appended to memory.md.

## Follow-up 1: Multi-disc album grouping
- `music_pipeline.py`: added `iter_album_groups()`; `process_folder()` accepts `tagged=` and `sources=`; multi-disc destinations keep CD1/CD2 subfolders; gap/complete/incomplete/review operate on whole album.
- `scan_folder()` made recursive so multi-disc destinations are read.
- `toolkit_core.py` + `music_toolkit.py`: review re-check/move and `review_accept` updated to recurse (`rglob`) for nested disc folders.
- Tests: grouping tests, multi-disc routing test, scan_folder nested test, review recheck/move nested tests.

## Follow-up 2: Restrict `/api/open`
- `toolkit_web.py`: `/api/open` returns 400 for non-directories (404 for missing).
- Tests: file rejection + folder acceptance.

## Follow-up 3: Requirements + README
- Added `requirements.txt`, `requirements-optional.txt`, `requirements-dev.txt`, `README.md`, `.gitignore`, `pytest.ini`.

## Improvements done
1. `QueueWriter` now matches "Analyzing album:" too (history source fix for multi-disc).
2. Desktop `SettingsTab.reset_paths` uses `PIPELINE_DEFAULT_PATHS`.
3. Stale `.partial.m4a` sweep (`_remove_stale_partials`) at conversion start, dry-run summarized.
4. Missing-disc detection in `find_release` (suspected missing disc → Incomplete/Review).
5. Dry-run no longer prompts for single-FLAC folders.
6. Duplicate tag scan parallelized (`ThreadPoolExecutor`).
7. Web review read/write race fixed (snapshot dict under lock).
8. Settings label corrected; CLI `--contact`/`--bitrate`/`--version` flags.
9. `pyproject.toml` added; web smoke tests added.
10. Consolidated Review + Plex scan/apply into `toolkit_core` (web + desktop delegate).
11. Checkbox visibility fixed (web `.tick` + desktop ttk indicator).
12. Restyled both UIs to Ember Pill Mobile (light theme, Nunito Sans, ember orange).
13. `memory.md` created.

## Test count
Started at 37; ended at 50 passing. py_compile clean on all four Python files throughout.