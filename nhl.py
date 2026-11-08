# Live hockey extras: shots on goal and power play for a game in progress.
# ESPN's scoreboard has neither, so for each live followed game we read two small things over plain HTTP:
# the top of the game summary (shots and power-play chances per team, only ~3KB of its 300KB) and the
# game's "situation" (is a power play on right now, 340 bytes).
import gc

import espn
import settings

CORE = "sports.core.api.espn.com"
SUMMARY = "/apis/site/v2/sports/hockey/nhl/summary?event=%s"
SITUATION = "/v2/sports/hockey/leagues/nhl/events/%s/competitions/%s/situation"
_chances = {}   # game id -> (away, home) power-play chances seen at the last look
_side = {}      # game id -> which team was last given a power play


def _stat(block, name):
    i = block.find(b'"name":"' + name + b'"')
    if i < 0:
        return None
    k = block.find(b'"displayValue":"', i)
    if k < 0:
        return None
    k += 16
    e = block.find(b'"', k)
    v = block[k:e]
    return int(v) if v.isdigit() else None


def parse_summary(head):
    """[(abbreviation, shots, power-play chances), ...] for the teams found at the top of a summary."""
    out = []
    for block in head.split(b'"team":{"id":"')[1:]:
        a = block.find(b'"abbreviation":"')
        if a < 0:
            continue
        a += 16
        shots = _stat(block, b"shotsTotal")
        ppo = _stat(block, b"powerPlayOpportunities")
        if shots is None or ppo is None:
            continue
        out.append((block[a:block.find(b'"', a)].decode(), shots, ppo))
    return out


def _read(host, path, limit, enough=None):
    conn, body = espn._open(host, path)
    data = body
    try:
        while len(data) < limit and not (enough and enough(data)):
            d = conn.read(1024)
            if not d:
                break
            data += d
    finally:
        conn.close()
    return data


def _two_teams(data):
    return len(parse_summary(data)) >= 2


def power_play_on(data):
    return b'"powerPlay":true' in data


def look(game):
    """Add 'sog' (away, home), 'pp' ('away'/'home'/None) and nothing else to a live hockey game dict."""
    eid = game.get("id")
    if not eid:
        return
    gc.collect()
    teams = parse_summary(_read(espn.HOST, SUMMARY % eid, 6000, _two_teams))
    by = {t[0]: t for t in teams}
    if game["away"] in by and game["home"] in by:
        away, home = by[game["away"]], by[game["home"]]
        game["sog"] = (away[1], home[1])
        old = _chances.get(eid)
        _chances[eid] = (away[2], home[2])
        if old:  # a new power-play chance for one team: that team has the power play
            if _chances[eid][0] > old[0]:
                _side[eid] = "away"
            elif _chances[eid][1] > old[1]:
                _side[eid] = "home"
    on = power_play_on(_read(CORE, SITUATION % (eid, eid), 1500))
    game["pp"] = _side.get(eid) if on else None
    game["pp_on"] = on  # on, but we may not know which team yet


def add_live(games):
    """Shots and power play for the (at most two) live games; a failed look just leaves them out."""
    n = 0
    for g in games:
        if g["state"] == "in" and n < 2:
            n += 1
            try:
                look(g)
            except Exception as e:
                print("hockey extras failed:", repr(e))
                settings.log("hockey extras failed", g["name"], repr(e))
