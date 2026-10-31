# Game logic: which games to show, how to word them, what a score change means.
import time

import settings
import sun
from board import AMBER, BLUE, GREY, WHITE

# Local time zone, weather and sun location come from config.json (see settings.py; the web page sets
# them). Defaults: Pacific time with US daylight saving, the default location.

LEAGUES = [
    {"sport": "baseball", "path": "baseball/mlb", "abbr": "LAD", "label": "LAD",
     "nick": "DODGERS", "color": (0, 110, 255), "early_exit": False, "mlb_team_id": 119, "team_slug": "lad", "rivals": ("SF", "SD")},
    {"sport": "football", "path": "football/nfl", "abbr": "SEA", "label": "SEA",
     "nick": "SEAHAWKS", "color": (105, 220, 40), "early_exit": True, "team_slug": "sea",
     "rivals": ("SF", "LAR")},
    {"sport": "hockey", "path": "hockey/nhl", "abbr": "SEA", "label": "KRK",
     "nick": "KRAKEN", "color": (70, 210, 230), "early_exit": False, "team_slug": "sea",
     "rivals": ("VAN", "VGK")},
]

DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

# A game takes over the panel when it starts and stays this long after the start.
# Until then the idle screen (next games + scores ticker) is shown.
SHOW_AFTER = 12 * 3600


def iso_to_epoch(iso):
    # "2026-10-26T00:20Z"
    return time.mktime((int(iso[0:4]), int(iso[5:7]), int(iso[8:10]),
                        int(iso[11:13]), int(iso[14:16]), 0, 0, 0, 0))


def _nth_sunday(year, month, n):
    wd = time.gmtime(time.mktime((year, month, 1, 12, 0, 0, 0, 0, 0)))[6]
    return 1 + (6 - wd) % 7 + 7 * (n - 1)


def utc_offset(t):
    """Hours from UTC for local time at epoch t (US daylight saving rules)."""
    std = settings.cfg["tz"]
    year = time.gmtime(t)[0]
    start = time.mktime((year, 3, _nth_sunday(year, 3, 2), 2 - std, 0, 0, 0, 0, 0))
    end = time.mktime((year, 11, _nth_sunday(year, 11, 1), 1 - std, 0, 0, 0, 0, 0))
    return std + 1 if start <= t < end else std


def local_now(t):
    """gmtime-style tuple for local time at epoch t."""
    return time.gmtime(t + utc_offset(t) * 3600)


def local_time_str(iso, now, with_day=True):
    t = iso_to_epoch(iso)
    lt = time.gmtime(t + utc_offset(t) * 3600)
    nl = time.gmtime(now + utc_offset(now) * 3600)
    h = lt[3]
    s = "%d:%02d%s" % (h % 12 or 12, lt[4], "A" if h < 12 else "P")
    if with_day and (lt[0], lt[1], lt[2]) != (nl[0], nl[1], nl[2]):
        s = DAYS[lt[6]] + " " + s
    return s


def status_text(g, now):
    """Full status line, e.g. 'Q3 5:21', '^7', 'FINAL', '7:10P'."""
    st = g["state"]
    d = g["detail"].upper()
    if st == "pre":
        return local_time_str(g["date"], now)
    if st == "post":
        return d if d.startswith("FINAL") else "FINAL"
    if g["sport"] == "baseball":
        w = d.split()
        n = "".join(c for c in w[1] if c.isdigit()) if len(w) > 1 else ""
        if n and w[0] in ("TOP", "BOT", "BOTTOM", "MID", "MIDDLE", "END"):
            return {"TOP": "^", "BOT": "v", "BOTTOM": "v", "MID": "MID ", "MIDDLE": "MID ", "END": "END "}[w[0]] + n
        return d[:12]
    if "HALF" in d:
        return "HALFTIME"
    p = g["period"]
    if g["sport"] == "football":
        tag = "OT" if p > 4 else "Q%d" % p
    else:
        tag = "SO" if p > 4 else "OT" if p > 3 else "P%d" % p
    if "END" in d:
        return "END " + tag
    return tag + " " + g["clock"]


def short_status(g, now):
    """Compact status for crowded layouts (no clock)."""
    st = g["state"]
    if st == "pre":
        return local_time_str(g["date"], now, with_day=False)
    if st == "post":
        return "F"
    s = status_text(g, now)
    return s.split()[0] if g["sport"] != "baseball" else s


CHAMPIONSHIPS = (("WORLD SERIES", "WS"), ("SUPER BOWL", "SB"), ("STANLEY CUP", "CUP"))
GOLD = (255, 200, 60)


def importance(g):
    """0 ordinary game, 1 playoff game, 2 championship (World Series, Super Bowl, Stanley Cup Final)."""
    if not g.get("playoff"):
        return 0
    n = g.get("note", "").upper()
    return 2 if any(k in n for k, _ in CHAMPIONSHIPS) else 1


def tag(g):
    """Short label for important games: WS, SB, CUP, or PO for any other playoff game."""
    if not importance(g):
        return None
    n = g.get("note", "").upper()
    for k, t in CHAMPIONSHIPS:
        if k in n:
            return t
    return "PO"


def rival(league, g):
    """True when one of our teams plays a rival (ours plays it, e.g. Dodgers vs Giants)."""
    if league["abbr"] not in (g["away"], g["home"]):
        return False
    other = g["home"] if g["away"] == league["abbr"] else g["away"]
    return other in league.get("rivals", ())


def make_view(league, g, now):
    ours = "away" if g["away"] == league["abbr"] else "home" if g["home"] == league["abbr"] else None
    pre = g["state"] == "pre"

    def lab(side):
        return league["label"] if ours == side else g[side]

    color = {"pre": BLUE, "in": AMBER, "post": GREY}[g["state"]]
    view = {
        "sport": league["sport"],
        "color": league["color"] if ours else GOLD,
        "ours": ours,
        "tag": tag(g) or ("RIV" if rival(league, g) else None),
        "away": lab("away"), "home": lab("home"),
        "away_score": None if pre else g["away_score"],
        "home_score": None if pre else g["home_score"],
        "status": status_text(g, now),
        "short": short_status(g, now),
        "status_color": color,
    }
    if g["sport"] == "baseball" and g["state"] == "in" and "bases" in g:
        # live baseball: board draws the diamond, out dots and ABS challenge squares
        view["live"] = {"bases": g["bases"], "outs": g["outs"], "count": g["count"], "abs": g["abs"]}
    return view


def game_key(sport, g):
    return (sport, g["name"], g["date"][:10])


def visible(leagues_data, now, clock_ok, league_wide=()):
    """[(league, game)] to put on screen: live first, then by importance, then start time.

    Our teams' games always get a place. league_wide is [(league, games)] for every game in
    each league; its playoff games get a place too, the finals ahead of the rest.
    """
    out = []
    seen = set()
    for league, games in leagues_data:
        for g in games:
            seen.add(game_key(league["sport"], g))
    for league, games in league_wide:
        for g in games:
            imp = importance(g)
            if not imp or game_key(league["sport"], g) in seen or g["state"] == "pre":
                continue
            if g["state"] == "post" and clock_ok and now - iso_to_epoch(g["date"]) > (8 if imp > 1 else 5) * 3600:
                continue
            out.append((league, g))
    for league, games in leagues_data:
        for g in games:
            if g["state"] == "pre":
                continue  # not started yet; the idle screen covers it
            if g["state"] == "post" and clock_ok and now - iso_to_epoch(g["date"]) > SHOW_AFTER:
                continue
            out.append((league, g))
    def rank(lg):
        league, g = lg
        mine = league["abbr"] in (g["away"], g["home"])
        return (g["state"] != "in", -(importance(g) + mine), g["date"])

    out.sort(key=rank)
    return out[:4]


MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def next_game_lines(league, nx, now):
    """Idle-screen text for a team's next game: [(text, role)], role 'opp' or 'when'."""
    sep = " @ " if " @ " in nx["name"] else " VS "
    away, home = nx["name"].split(sep)[:2]
    opp = ("VS " + away) if home == league["abbr"] else ("AT " + home)
    d = nx["date"]
    if nx["time_valid"]:
        until = iso_to_epoch(d) - now
        if 0 < until < 3600:
            when = "IN %d MIN" % ((until + 59) // 60)
        else:
            when = local_time_str(d, now)
    else:  # date known, time still TBD
        when = "%s %d" % (MONTHS[int(d[5:7]) - 1], int(d[8:10]))
    return [(opp, "rival" if (home if home != league["abbr"] else away) in league.get("rivals", ()) else "opp"),
            (when, "when")]


def record_text(nx):
    """'8-5-1 L2' from a team's next-event record and streak, or '' when unknown."""
    rec = nx.get("record") if nx else None
    if not rec:
        return ""
    streak = nx.get("streak") or 0
    return rec + (" %s%d" % ("W" if streak > 0 else "L", abs(streak)) if streak else "")


def next_sun(now):
    """('SUNRISE' or 'SUNSET', '7:31A', minutes until it) for the next one at our location."""
    base = now - now % 86400
    best = None
    for k in (-1, 0, 1):
        y, m, d = time.gmtime(base + k * 86400)[:3]
        for name, hours in zip(("SUNRISE", "SUNSET"), sun.times(settings.cfg["lat"], settings.cfg["lon"], y, m, d)):
            if hours is None:
                continue
            t = base + k * 86400 + int(hours * 3600)
            if t > now and (best is None or t < best[0]):
                best = (t, name)
    if best is None:
        return None
    t, name = best
    lt = time.gmtime(t + utc_offset(t) * 3600)
    h = lt[3]
    return name, "%d:%02d%s" % (h % 12 or 12, lt[4], "A" if h < 12 else "P"), (t - now) // 60


def banner(league, g, side, delta):
    """(text, ours) describing a score change of `delta` for `side`."""
    ours = (g[side] == league["abbr"])
    sport = league["sport"]
    if not ours:
        return "%s +%d" % (g[side], delta), False
    if sport == "hockey":
        return ("GOAL!" if delta == 1 else "%d GOALS!" % delta), True
    if sport == "football":
        if delta >= 6:
            return "TOUCHDOWN!", True
        return {3: "FIELD GOAL!", 2: "SAFETY!", 1: "EXTRA POINT!"}.get(delta, "+%d!" % delta), True
    return ("RUN!" if delta == 1 else "%d RUNS!" % delta), True


def result_text(won, mine, theirs):
    """Word for the end-of-game animation."""
    if won:
        return "SHUTOUT!" if theirs == 0 else "WIN!"
    return "LOSS"


NEUTRAL = (175, 175, 175)  # teams that aren't ours
TAGS = {"baseball": "MLB", "football": "NFL", "hockey": "NHL"}
MARQUEE_BEFORE = 20 * 3600
MARQUEE_AFTER = 14 * 3600


def marquee_parts(all_games, now, clock_ok):
    """Ticker text for every game in the league scoreboards, as [(text, colour)].

    all_games is [(league, games)]; our own teams are drawn in their team colour.
    """
    parts = []
    for league, games in all_games:
        picked = []
        for g in games:
            if g["state"] != "in" and clock_ok:
                start = iso_to_epoch(g["date"])
                if g["state"] == "pre" and start - now > MARQUEE_BEFORE:
                    continue
                if g["state"] == "post" and now - start > MARQUEE_AFTER:
                    continue
            picked.append(g)
        if not picked:
            continue
        picked.sort(key=lambda g: (g["state"] != "in", g["date"]))
        parts.append((TAGS[league["sport"]], WHITE))
        for g in picked:
            ca = league["color"] if g["away"] == league["abbr"] else NEUTRAL
            ch = league["color"] if g["home"] == league["abbr"] else NEUTRAL
            if importance(g):
                parts.append((tag(g), GOLD))
            if g["state"] == "pre":
                parts += [(g["away"], ca), ("VS", GREY), (g["home"], ch),
                          (local_time_str(g["date"], now), BLUE)]
            else:
                parts += [(g["away"], ca), (str(g["away_score"]), WHITE),
                          (g["home"], ch), (str(g["home_score"]), WHITE),
                          (short_status(g, now), AMBER if g["state"] == "in" else GREY)]
            parts.append(("|", (90, 90, 90)))
    return parts or [("NO SCORES TODAY", GREY)]
