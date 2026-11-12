"""Rebuild web/icons.js from the Solar icon set (@iconify-json/solar).

Only the icons the web app uses are bundled, so the app works offline.
Usage:
    npm install @iconify-json/solar@1.2.13     # pinned: this is the release the bundle was built from
    python tools/build_icons.py path/to/node_modules/@iconify-json/solar

Icons are found by scanning web/app.js and web/index.html for quoted names such as
"name-bold" and solar:name. A name missing from the set is an error, so a blank icon can't ship silently.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = ("/* Solar icon set (Iconify, CC BY 4.0, by 480 Design), only the icons this app uses,\n"
          "   bundled so the toolkit works without internet. Regenerate with tools/build_icons.py. */\n")
ELEMENT_JS = ROOT / "tools" / "icon_element.js"   # fixed <iconify-icon> element code, kept beside the script
LEGACY_JSON = ROOT / "tools" / "legacy_icons.json"  # bodies with no equivalent in the pinned Solar release
ALIASES = {"magnifer-bold": "magnifier-bold"}      # same drawing, renamed in Solar


def used_icon_names() -> set[str]:
    names = set()
    for f in [ROOT / "web" / "app.js", ROOT / "web" / "index.html"]:
        text = f.read_text(encoding="utf-8")
        names |= set(re.findall(r"solar:([a-z0-9-]+)", text))
        # any quoted icon-style name: ic("x-bold"), chip(..., "x-linear"), etc.
        names |= set(re.findall(r'"([a-z0-9]+(?:-[a-z0-9]+)*-(?:bold|linear|line-duotone|broken|outline|bold-duotone))"', text))
    return names


def main(solar_dir: str) -> int:
    icons = json.loads((Path(solar_dir) / "icons.json").read_text(encoding="utf-8"))["icons"]
    wanted = sorted(used_icon_names())
    legacy = json.loads(LEGACY_JSON.read_text(encoding="utf-8"))
    bodies = {}
    for n in wanted:
        if n in icons:
            bodies[n] = icons[n]["body"]
        elif ALIASES.get(n) in icons:
            bodies[n] = icons[ALIASES[n]]["body"]
        elif n in legacy:
            bodies[n] = legacy[n]
        else:
            print("Not in the Solar set:", n)
            return 1
    js = HEADER + "window.SOLAR_ICONS = " + json.dumps(bodies, ensure_ascii=False, separators=(",", ":")) + ";\n"
    js += ELEMENT_JS.read_text(encoding="utf-8")
    (ROOT / "web" / "icons.js").write_text(js, encoding="utf-8")
    print(f"wrote web/icons.js with {len(wanted)} icons")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
