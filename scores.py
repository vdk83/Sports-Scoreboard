# Game logic: which games to show, how to word them, what a score change means.
import time

import settings
import sun
import teams
from board import AMBER, BLUE, GREY, WHITE

# Local time zone, weather and sun location come from config.json (see settings.py; the web page sets
# them). Defaults: Pacific time with US daylight saving, with the default location set in settings.py.

# The three sports we know about, and what to fetch for each (the feeds are per sport).
SPORTS = [
    {"sport": "baseball", "path": "baseball/mlb", "early_exit": False, "abbr": "", "label": "", "rivals": (), "nick": "MLB"},
    {"sport": "football", "path": "football/nfl", "early_exit": True, "abbr": "", "label": "", "rivals": (), "nick": "NFL"},
    {"sport": "hockey", "path": "hockey/nhl", "early_exit": False, "abbr": "", "label": "", "rivals": (), "nick": "NHL"},
    {"sport": "basketball", "path": "basketball/nba", "early_exit": True, "abbr": "", "label": "", "rivals": (), "nick": "NBA"},
    {"sport": "soccer", "path": "soccer/usa.1", "early_exit": True, "abbr": "", "label": "", "rivals": (), "nick": "MLS"},
]
SPORT_INDEX = {s["sport"]: i for i, s in enumerate(SPORTS)}

# LEAGUES has one entry per team we follow (any number per sport), rebuilt from the settings by apply_teams().
# It is changed in place, so every module that imported it sees the change.
LEAGUES = []
MAX_PER_SPORT = 4
ORIGINAL = (("baseball", "LAD"), ("football", "SEA"), ("hockey", "SEA"))  # the celebration cameos are drawn for these
RIVALS = {("baseball", "LAD"): ("SF", "SD"), ("football", "SEA"): ("SF", "LAR"), ("hockey", "SEA"): ("VAN", "VGK"),
          ("basketball", "GS"): ("LAL", "LAC"), ("soccer", "SEA"): ("POR", "VAN", "LAFC")}


def find_team(sport, abbr):
    """The teams.py row (full name, nickname, abbreviation, ESPN page, colour, MLB id) or None."""
    for row in teams.TEAMS.get(sport, ()):
        if row[2] == abbr:
            return row
    return None


def follow_entry(sport, abbr):
    """The LEAGUES entry for a followed team, or None."""
    for f in LEAGUES:
        if f["sport"] == sport and f["abbr"] == abbr:
            return f
    return None


def followed(sport, abbr):
    return follow_entry(sport, abbr) is not None


def entry_for(sport, g):
    """The followed team playing in game g (the first, if both are), else the sport's own entry."""
    for f in LEAGUES:
        if f["sport"] == sport and f["abbr"] in (g["away"], g["home"]):
            return f
    return SPORTS[SPORT_INDEX[sport]]


def team_color(sport, abbr):
    f = follow_entry(sport, abbr)
    return f["color"] if f else NEUTRAL


def chosen(sport):
    """The followed abbreviations in settings for a sport: valid ones only, no repeats, at least one."""
    out = []
    for tok in settings.cfg["team_" + sport].split(","):
        tok = tok.strip().upper()
        if tok and tok not in out and find_team(sport, tok):
            out.append(tok)
    return out[:MAX_PER_SPORT] or [settings.DEFAULTS["team_" + sport]]


def apply_teams():
    """Rebuild LEAGUES from the settings. Returns the indexes (into SPORTS) of sports whose teams changed."""
    old = [(f["sport"], f["abbr"]) for f in LEAGUES]
    entries = []
    for s in SPORTS:
        sport = s["sport"]
        abbrs = chosen(sport)
        settings.cfg["team_" + sport] = ",".join(abbrs)
        for abbr in abbrs:
            name, nick, abbr, slug, color, mlb_id = find_team(sport, abbr)
            e = {"sport": sport, "path": s["path"], "abbr": abbr, "nick": nick, "color": color,
                 "label": "KRK" if (sport, abbr) == ("hockey", "SEA") else abbr, "early_exit": s["early_exit"],
                 "team_slug": slug, "rivals": RIVALS.get((sport, abbr), ())}
            if sport == "baseball":
                e["mlb_team_id"] = mlb_id
            entries.append(e)
    LEAGUES[:] = entries
    new = [(f["sport"], f["abbr"]) for f in LEAGUES]
    changed = []
    for pair in old + new:
        if (pair in old) != (pair in new) and SPORT_INDEX[pair[0]] not in changed:
            changed.append(SPORT_INDEX[pair[0]])
    return changed


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
    if "HALF" in d or (g["sport"] == "soccer" and d.startswith("HT")):
        return "HALFTIME"
    p = g["period"]
    if g["sport"] == "soccer":
        return g["clock"] or d[:12]  # the minute, like 67' or 90'+3'
    if g["sport"] == "football":
        tag = "OT" if p > 4 else "Q%d" % p
    elif g["sport"] == "basketball":
        tag = "Q%d" % p if p <= 4 else "OT" if p == 5 else "%dOT" % (p - 4)
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
    if g["sport"] == "baseball":
        return s
    return s.split()[0] + (" PP" if g.get("pp_on") else "")


CHAMPIONSHIPS = (("WORLD SERIES", "WS"), ("SUPER BOWL", "SB"), ("STANLEY CUP", "CUP"), ("NBA FINALS", "NBA"),
                 ("MLS CUP", "MLS"))
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
        "close": is_close(g),
    }
    if g["sport"] == "baseball" and g["state"] == "in" and "bases" in g:
        # live baseball: board draws the diamond, out dots and ABS challenge squares
        view["live"] = {"bases": g["bases"], "outs": g["outs"], "count": g["count"], "abs": g["abs"]}
    if g["sport"] == "hockey" and g["state"] == "in" and g.get("sog"):
        # live hockey: shots on goal (away, home) and the team on a power play, if any
        view["hockey"] = {"sog": g["sog"], "pp": g.get("pp"), "pp_on": g.get("pp_on", False)}
    if g["sport"] == "football" and g["state"] == "in" and 1 <= g["period"] <= 4:
        view["quarter"] = g["period"]
    return view


def game_key(sport, g):
    return (sport, g["name"], g["date"][:10])


def visible(leagues_data, now, clock_ok, league_wide=()):
    """[(league, game)] to put on screen: live first, then by importance, then start time.

    Our teams' games always get a place. league_wide is [(league, games)] for every game in
    each league; its playoff games get a place too, the finals ahead of the rest. Each game is
    paired with the followed team playing in it (or the sport's own entry).
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
            out.append((entry_for(league["sport"], g), g))
    done = set()
    for league, games in leagues_data:
        for g in games:
            key = game_key(league["sport"], g)
            if key in done:  # both teams followed: one card for the game
                continue
            if g["state"] == "pre":
                continue  # not started yet; the idle screen covers it
            if g["state"] == "post" and clock_ok and now - iso_to_epoch(g["date"]) > SHOW_AFTER:
                continue
            done.add(key)
            out.append((entry_for(league["sport"], g), g))

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


def sun_today(now):
    """(sunrise, sunset) as epoch seconds for the local day containing `now`; either may be None."""
    lt = local_now(now)
    base = now - now % 86400
    out = [None, None]
    for k in (-1, 0, 1):  # the UTC date holding the event can differ from the local date
        y, m, d = time.gmtime(base + k * 86400)[:3]
        for j, hours in enumerate(sun.times(settings.cfg["lat"], settings.cfg["lon"], y, m, d)):
            if hours is None:
                continue
            t = base + k * 86400 + int(hours * 3600)
            if local_now(t)[:3] == lt[:3]:
                out[j] = t
    return tuple(out)


def is_close(g):
    """A live game that is tight late on: baseball 9th+ within 1, hockey 3rd+ within 1, football 4th+ within 8,
    basketball 4th+ within 5, soccer 2nd half within 1."""
    if g["state"] != "in":
        return False
    try:
        diff = abs(g["away_score"] - g["home_score"])
        p = g["period"] or 0
        if g["sport"] == "baseball":
            return p >= 9 and diff <= 1
        if g["sport"] == "hockey":
            return p >= 3 and diff <= 1
        if g["sport"] == "football":
            return p >= 4 and diff <= 8
        if g["sport"] == "basketball":
            return p >= 4 and diff <= 5
        if g["sport"] == "soccer":
            return p >= 2 and diff <= 1
    except TypeError:
        pass
    return False


def banner(league, g, side, delta):
    """(text, ours) describing a score change of `delta` for `side`."""
    sport = league["sport"]
    ours = followed(sport, g[side])
    if not ours:
        return "%s +%d" % (g[side], delta), False
    if sport in ("hockey", "soccer"):
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
TAGS = {"baseball": "MLB", "football": "NFL", "hockey": "NHL", "basketball": "NBA", "soccer": "MLS"}
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
            ca = team_color(league["sport"], g["away"])
            ch = team_color(league["sport"], g["home"])
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


apply_teams()  # follow the teams in settings from the start
