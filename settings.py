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
REMINDERS = "reminders.json"
MAX_REMINDERS = 10
REMIND_HOURS = 3  # a reminder with a time stays up this long
LOG_LINES = 40

DEFAULTS = {
    "display": 1,    # 0 = panel dark (the board keeps running), 1 = on
    "mode": 0,       # 0 NORMAL, 1 CLOCK, 2 ART
    "bright": 0,     # 0 = automatic by time of day, else a fixed percent
    "cameos": 1,     # index into app.CAMEO_RATES: 0 often, 1 normal, 2 rare, 3 off
    "lat": 37.03,    # for the weather and sunrise/sunset
    "lon": -122.12,
    "tz": -8,        # hours from UTC in winter (US daylight saving is applied on top)
    "qs": 0,         # quiet hours: the panel goes dark from hour qs (0-23)...
    "qe": 0,         # ...until hour qe. qs == qe means no quiet hours
    "sunbright": 1,  # 1 = automatic brightness follows sunrise/sunset, 0 = fixed clock hours
    "team_baseball": "LAD",  # the teams followed in each sport (up to 4, comma separated), by the abbreviation
    "team_football": "SEA",  # its game feed uses (scores.apply_teams checks these against teams.py)
    "team_hockey": "SEA",
    "team_basketball": "GS",
    "team_soccer": "SEA",
}
LIMITS = {"display": (0, 1), "mode": (0, 2), "bright": (0, 100), "cameos": (0, 3), "lat": (-90, 90), "lon": (-180, 180),
          "tz": (-12, 14), "qs": (0, 23), "qe": (0, 23), "sunbright": (0, 1)}

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
    if isinstance(DEFAULTS[key], str):  # team abbreviations, comma separated: up to 4, each 2-5 letters or digits
        toks = [t.strip().upper() for t in str(value).split(",") if t.strip()]
        if not 1 <= len(toks) <= 4 or any(not 2 <= len(t) <= 5 or not all(c.isalpha() or c.isdigit() for c in t) for t in toks):
            raise ValueError(key)
        return ",".join(toks)
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


def import_json(text):
    """Apply a settings export (JSON text). Returns how many values were accepted."""
    try:
        d = json.loads(text)
    except ValueError:
        return 0
    if not isinstance(d, dict):
        return 0
    return sum(1 for k, v in d.items() if set_value(k, v))


def quiet_now(hour):
    """True during the quiet hours (which may wrap past midnight)."""
    s, e = cfg["qs"], cfg["qe"]
    if s == e:
        return False
    return s <= hour < e if s < e else hour >= s or hour < e


# -- reminders ----------------------------------------------------------------
# Each is [text, date "YYYY-MM-DD", time "HH:MM" or "", repeat]; repeat 0 = once on that date,
# 1 = every day from that date, 2 = every week on that date's weekday. They show on the idle screen.
reminders = []


def _weekday(y, m, d):
    t = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    y -= m < 3
    return (y + y // 4 - y // 100 + y // 400 + t[m - 1] + d + 6) % 7  # 0 = Monday


def load_reminders():
    saved = _read(REMINDERS)
    del reminders[:]
    if isinstance(saved, list):
        for r in saved:
            if isinstance(r, list) and len(r) == 4:
                try:
                    add_reminder(*r, save_now=False)
                except (TypeError, ValueError):
                    pass


def add_reminder(text, date, hhmm="", repeat=0, save_now=True):
    """Validate and add one. Raises ValueError when something is wrong."""
    text = " ".join(str(text).upper().split())[:30]
    if not text or len(reminders) >= MAX_REMINDERS:
        raise ValueError("text")
    y, m, d = [int(x) for x in str(date).split("-")]
    if not (2020 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        raise ValueError("date")
    hhmm = str(hhmm).strip()
    if hhmm:
        h, mi = [int(x) for x in hhmm.split(":")[:2]]
        if not (0 <= h <= 23 and 0 <= mi <= 59):
            raise ValueError("time")
        hhmm = "%02d:%02d" % (h, mi)
    repeat = int(repeat)
    if repeat not in (0, 1, 2):
        raise ValueError("repeat")
    reminders.append([text, "%04d-%02d-%02d" % (y, m, d), hhmm, repeat])
    if save_now:
        _write(REMINDERS, reminders)


def delete_reminder(i):
    if 0 <= i < len(reminders):
        del reminders[i]
        _write(REMINDERS, reminders)
        return True
    return False


def active_reminders(lt):
    """Texts to show now. lt is a local time tuple (year, month, day, hour, minute, ...). Finished one-offs go."""
    out = []
    today = (lt[0], lt[1], lt[2])
    mins = lt[3] * 60 + lt[4]
    gone = []
    for r in reminders:
        y, m, d = [int(x) for x in r[1].split("-")]
        if r[3] == 0 and (y, m, d) < today:
            gone.append(r)
            continue
        if (y, m, d) > today:
            continue
        if r[3] == 0 and (y, m, d) != today:
            continue
        if r[3] == 2 and _weekday(y, m, d) != _weekday(*today):
            continue
        if r[2]:
            start = int(r[2][:2]) * 60 + int(r[2][3:])
            if not start <= mins < start + REMIND_HOURS * 60:
                continue
        out.append(r[0])
    if gone:
        for r in gone:
            reminders.remove(r)
        _write(REMINDERS, reminders)
    return out


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
load_reminders()
