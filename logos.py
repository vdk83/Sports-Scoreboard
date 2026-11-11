# Team logos for the game views. The pixels live in logos_<sport>.py (made by make_logos.py); a sport's file is
# imported only to copy out the one logo that is needed, then dropped again to save RAM.
import sys

import teams

SIZE = 10
_cache = {}


def get(sport, abbr):
    """SIZE*SIZE bytes (RGB332, 0 = see-through) for a team, or None when there is no logo."""
    key = (sport, abbr)
    if key in _cache:
        return _cache[key]
    px = None
    rows = teams.TEAMS.get(sport, ())
    for i in range(len(rows)):
        if rows[i][2] == abbr:
            name = "logos_" + sport
            try:
                mod = __import__(name)
                px = bytes(mod.DATA[i * SIZE * SIZE:(i + 1) * SIZE * SIZE])
            except (ImportError, AttributeError):
                px = None
            sys.modules.pop(name, None)
            if px is not None and len(px) != SIZE * SIZE:
                px = None
            break
    if len(_cache) > 12:
        _cache.clear()
    _cache[key] = px
    return px


def color(v):
    """(r, g, b) for one RGB332 byte."""
    return ((v >> 5) * 255 // 7, ((v >> 2) & 7) * 255 // 7, (v & 3) * 85)
