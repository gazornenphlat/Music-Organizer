"""Test bootstrap.

The pipeline imports its optional runtime dependencies at module import time.
Most of the tests exercise pure functions, so stub anything that is missing
instead of requiring a full music-toolkit install just to run pytest.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _stub_if_missing(name: str, **attrs) -> None:
    try:
        __import__(name)
    except ImportError:
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module


# musicbrainzngs calls these two at import time; the tests never hit the network.
_stub_if_missing("musicbrainzngs", set_useragent=lambda *a, **k: None,
                 set_rate_limit=lambda *a, **k: None)
_stub_if_missing("tqdm", tqdm=type("tqdm", (), {}))
_stub_if_missing("mutagen")
