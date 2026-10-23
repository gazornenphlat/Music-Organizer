# CLAUDE.md

Guidance for Claude when working on this codebase. For history and the reasoning behind decisions, see `memory.md`.

## Project
Personal music-library toolkit for Windows (library on `M:`): FLAC→M4A conversion, beets + MusicBrainz verification and sorting, duplicate cleanup (music and Plex). There are two front ends, a Tk desktop app and a Flask web app, over shared core logic.

## Layout
```
music_pipeline.py   engine + command line; stage 1 convert, stage 2 cleanup/sort, MusicBrainz matching
toolkit_core.py     shared logic, no UI imports; run_pipeline(), dupes, tag health, Plex rules, review helpers, settings, History
music_toolkit.py    Tk desktop app (imports * from toolkit_core); theme in T / FONTS / apply_theme()
toolkit_web.py      Flask server: /api/* JSON endpoints, /api/events SSE, Job runner, Hub (event bus)
web/                index.html, app.js (vanilla JS, no build step), style.css (design tokens), icons.js, fonts/
fonts/              TTFs for Tk (loaded privately on Windows)
config.yaml         beets config
```
`flac_to_m4a.py`, `leftover_cleanup.py`, `find_music_dupes.py`, `delete_dupes.py` and `plex_dedup.py` are old originals. Don't edit them.

## Commands
```
python music_toolkit.py                      # desktop app
python toolkit_web.py [--lan] [--port N]     # web app on 127.0.0.1:8765
python music_pipeline.py FOLDER --dry-run    # command line
python -m pyflakes *.py && node --check web/app.js   # lint
```
Dependencies: `tqdm mutagen musicbrainzngs flask`; optional `send2trash plexapi pyacoustid`; ffmpeg and ffprobe on PATH.

## Architecture rules
- **New logic goes in `toolkit_core.py` or `music_pipeline.py`, never in a UI file.** Both front ends must behave the same.
- **Long jobs report through a bus**: any object with `post(kind, *payload)`. The Tk `UiBus` queues events for the Tk main loop; the web `Hub` streams them to browsers as SSE. Event names: `log`, `slots_init`, `slot`, `overall`, `beets_progress`, `pipeline_done`, `<job>_progress`, `<job>_done`, `ask`/`ask_done`, `plex_log`.
- **Tk:** never touch Tk widgets or variables from worker threads. Read Tk values on the main thread and pass them in, and post results back through the bus.
- **Web:** high-frequency event kinds are coalesced in `Hub.COALESCE`. Any non-coalesced event first flushes the queued ones, so progress never arrives after a "done" message. Keep that ordering.
- **Patching `music_pipeline`:** `run_pipeline()` monkey-patches `mp.act`, `convert_file`, `convert_all`, `process_folder`, `ask_choice` and `BEETS_PROGRESS`/`CANCEL_EVENT`, and restores the `_MP_*` originals in its `finally` block. Any new patch must be restored the same way.
- **Filesystem changes in the pipeline go through `act(desc, fn, ...)`** so that dry run, history logging and the Recycle Bin all work.
- **Settings:** one JSON file (`music_toolkit_settings.json`) shared by both apps. To add a setting, add a key to `default_settings()` in core; the web server accepts only keys listed there. Never send the Plex token to the browser.
- **Output folders:** `PATH_SETTINGS` + `apply_paths_from()` push the configured folders into `mp`, and `PIPELINE_DEFAULT_PATHS` holds the originals.

## Safety invariants (don't weaken)
- Dry run is on by default and is never persisted. Live runs need confirmation.
- Originals are deleted only after verified output (duration check). Conversions write to `*.partial.m4a` first.
- Plex: plan first, then apply. Refuse to delete every copy in a group. Folders are removed only inside a library root, never the root itself.
- Music duplicates with a length difference over 2 s, and Plex groups with a length difference over 5%, are never auto-ticked.
- The web server binds to 127.0.0.1 unless `--lan` is used; `--lan` requires the token.
- Log every move and delete via `History.write(tab, action, detail)`.

## UI / design
- Follow the "Ember Pill Mobile" design (light theme):
  - **Colours:** bg #FFFFFF, surface #FFFFFF, surface-alt #F2F2F7, on-surface #000000, muted #6C6C70, border #E5E5EA, primary #F37F46, success #34C759, error #FF3B30, warning #FF9500, accent-blue #007AFF, accent-indigo #5856D6, accent-yellow #F5C842.
  - **Typefaces:** Nunito Sans (web) / Manrope + Space Grotesk (desktop fallback). No third typeface.
  - **Shape language:** pills for actions/nav, 28-32px cards, 14px chips, floating glass tab capsule.
  - **Colours for status:** semantic colours appear only as text or tinted badges, never as solid fills.
- **Web:**
  - Use the CSS tokens and classes in `style.css`: `card`, `card-elevated`, `btn primary`, `chip`, `segmented`, `badge t-*`, `circle c-*`, `list-row`, `divided`, `progress`.
  - Icons are `ic("name-bold")` / `<iconify-icon icon="solar:...">` and render from local `web/icons.js`, so the app works offline. **After using a new icon, regenerate `icons.js`** from `@iconify-json/solar` (npm). Missing icons render blank.
  - No CDNs, no build step, no frameworks.
- **Tk:** use `T[...]` colours and `FONTS[...]`. Buttons are styled by text prefix in `style_buttons()` (`Accent.TButton` / `Danger.TButton`). Don't set a global `*Font` option; it overrides ttk style fonts.

## Gotchas
- ffmpeg progress must use `-progress pipe:1` (key=value on stdout). The `-stats` line differs between builds.
- beets output is parsed per album from `"<folder> (N items)"` lines. Run beets with `PYTHONUNBUFFERED=1`.
- The beets import log directory must exist, or beets refuses to start.
- The MusicBrainz cache is `mb_cache_v3.json`, with key prefixes `s:` (search), `id:` (release) and `rec:` (recording search). Don't cache network failures.
- When killing a test server by matching the command line, don't use a pattern that also matches your own shell command (it kills itself).

## Testing
- Test suite: `python -m pytest -q` (50 tests). Test with synthetic audio from ffmpeg (`-f lavfi -i sine=...` with `-metadata` tags) in a scratch folder, with a settings file pointing the output folders there.
- **Web:** run the server and drive `/api/*` with curl. Listen on `/api/events` to check events. Check layout with Playwright screenshots at 1280 px and 390 px wide.
- **Tk:** run under Xvfb (Python with Tk) and screenshot each notebook tab.
- **Not yet tested:** Windows, a real Plex server, live MusicBrainz and Discogs. Say so when relevant.

## Working style for this user
- They tend to ask for whole features at once ("add all suggestions", "rewrite as necessary"). Implement everything asked, test it, then list concrete improvement suggestions at the end.
- Deliver updated files, keep the project copies in sync (`claude/...`), and update `memory.md` when decisions change.
