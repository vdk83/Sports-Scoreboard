# Settings, log and cache kept in the board's flash, so a restart or a power cut keeps them.
#
#   config.json  what the web page (ota.py -> app.py) changes; created on first save
#   log.txt      the last log lines, saved when the board is about to restart
#   cache.json   the last schedule/ticker/weather, so the screen is not empty after a restart
#
# Plain Python on purpose: it also runs on a computer for the tests.
import json
import time

CONFIG = "config.json"
LOGFILE = "log.txt"
CACHE = "cache.json"
LOG_LINES = 40

DEFAULTS = {
    "display": 1,    # 0 = panel dark (the board keeps running), 1 = on
    "mode": 0,       # 0 NORMAL, 1 CLOCK, 2 ART
    "bright": 0,     # 0 = automatic by time of day, else a fixed percent
    "cameos": 1,     # index into app.CAMEO_RATES: 0 often, 1 normal, 2 rare, 3 off
    "lat": 37.03,    # for the weather and sunrise/sunset; the default location
    "lon": -122.12,
    "tz": -8,        # hours from UTC in winter (US daylight saving is applied on top)
}
LIMITS = {"display": (0, 1), "mode": (0, 2), "bright": (0, 100), "cameos": (0, 3), "lat": (-90, 90), "lon": (-180, 180),
          "tz": (-12, 14)}

cfg = dict(DEFAULTS)
_lines = []


def _read(name):
    try:
        with open(name) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write(name, obj):
    try:
        with open(name, "w") as f:
            json.dump(obj, f)
        return True
    except OSError:
        return False


def load():
    saved = _read(CONFIG)
    if isinstance(saved, dict):
        for k in DEFAULTS:
            if k in saved:
                try:
                    cfg[k] = _clean(k, saved[k])
                except (TypeError, ValueError):
                    pass


def _clean(key, value):
    """The value as the right type and inside its limits, or ValueError."""
    v = float(value) if isinstance(DEFAULTS[key], float) else int(float(value))
    lo, hi = LIMITS[key]
    if not lo <= v <= hi:
        raise ValueError(key)
    return v


def set_value(key, value):
    """Change one setting (the value may be text from a web form). True if it was accepted."""
    if key not in DEFAULTS:
        return False
    try:
        cfg[key] = _clean(key, value)
    except (TypeError, ValueError):
        return False
    return True


def save():
    return _write(CONFIG, cfg)


# -- log ----------------------------------------------------------------------
def _uptime():
    try:
        return time.ticks_ms() // 1000
    except AttributeError:  # not on the board
        return int(time.monotonic())


def log(*parts):
    """Print a line and keep it for the /log page."""
    msg = " ".join(str(p) for p in parts)
    print(msg)
    _lines.append("%d %s" % (_uptime(), msg[:120]))
    if len(_lines) > LOG_LINES:
        del _lines[0]


def save_log():
    """Keep the recent lines across a restart (flash writes are slow, so only before one)."""
    try:
        with open(LOGFILE, "w") as f:
            f.write("\n".join(_lines))
    except OSError:
        pass


def read_log():
    try:
        with open(LOGFILE) as f:
            before = f.read()
    except OSError:
        before = ""
    return "-- before the last restart --\n%s\n-- since then (seconds since power-on) --\n%s\n" % (
        before, "\n".join(_lines))


# -- cache --------------------------------------------------------------------
def save_cache(obj):
    return _write(CACHE, obj)


def load_cache():
    c = _read(CACHE)
    return c if isinstance(c, dict) else None


load()
