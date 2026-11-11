# MLB Stats API reader. ESPN's baseball feed has no runners/outs/ABS data,
# so baseball comes from MLB directly. Responses are asked to be trimmed to
# ~1KB per game with `fields=`, which is small enough to json.loads().
import gc
import json
import time

import espn

HOST = "statsapi.mlb.com"
FIELDS = ("dates,games,gamePk,gameType,gameDate,status,abstractGameState,detailedState,"
          "teams,away,home,score,team,abbreviation,linescore,currentInning,"
          "currentInningOrdinal,inningState,scheduledInnings,outs,balls,strikes,"
          "offense,first,second,third,id,defense,pitcher,batter,fullName")
ABS_FIELDS = "gameData,absChallenges,hasChallenges,away,home,remaining"
SKIP = ("Postponed", "Cancelled", "Canceled")


def _get_json(path, limit=50000):
    s, body = espn._open(HOST, path)
    parts = [body]
    n = len(body)
    try:
        while True:
            d = s.read(1024)
            if not d:
                break
            parts.append(d)
            n += len(d)
            if n > limit:
                raise OSError("response too big")
    finally:
        s.close()
    return json.loads(b"".join(parts))


def _day(t):
    y, m, d = time.gmtime(t)[:3]
    return "%04d-%02d-%02d" % (y, m, d)


def convert(game):
    """MLB schedule entry -> the same game dict ESPN games use, plus baseball extras."""
    status = game["status"]
    detailed = status.get("detailedState", "")
    if detailed in SKIP:
        return None
    state = {"Preview": "pre", "Live": "in", "Final": "post"}.get(status.get("abstractGameState"), "pre")
    ls = game.get("linescore") or {}
    inning = ls.get("currentInning") or 0
    if state == "in":
        if inning and ls.get("inningState"):
            detail = "%s %s" % (ls["inningState"], ls.get("currentInningOrdinal", ""))
        else:
            detail = detailed or "Warmup"
    elif state == "post":
        extra = inning and inning != game.get("scheduledInnings", 9)
        detail = "Final/%d" % inning if extra else "Final"
    else:
        detail = detailed
    off = ls.get("offense") or {}
    pitcher = ((ls.get("defense") or {}).get("pitcher") or {}).get("fullName")  # the team in the field's pitcher
    batter = (off.get("batter") or {}).get("fullName")
    away = game["teams"]["away"]
    home = game["teams"]["home"]
    aa = away["team"]["abbreviation"]
    ha = home["team"]["abbreviation"]
    gt = game.get("gameType", "R")
    return {
        "sport": "baseball",
        "playoff": gt in ("F", "D", "L", "W"),
        "note": {"W": "World Series", "L": "League Championship", "D": "Division Series",
                 "F": "Wild Card"}.get(gt, ""),
        "name": "%s @ %s" % (aa, ha),
        "date": game["gameDate"][:16] + "Z",
        "away": aa, "away_score": away.get("score", 0),
        "home": ha, "home_score": home.get("score", 0),
        "clock": "", "period": inning, "state": state, "detail": detail,
        "pk": game["gamePk"],
        "bases": ("first" in off, "second" in off, "third" in off),
        "outs": ls.get("outs", 0),
        "count": "%d-%d" % (ls.get("balls", 0), ls.get("strikes", 0)),
        "pitcher": espn.last_name(pitcher) if pitcher else "",
        "batter": espn.last_name(batter) if batter else "",
        "abs": None,
    }


def abs_challenges(pk):
    """{'away': n, 'home': n} challenges remaining, or None if the game has none."""
    try:
        d = _get_json("/api/v1.1/game/%d/feed/live?fields=%s" % (pk, ABS_FIELDS), 4000)
        a = d["gameData"]["absChallenges"]
        if a.get("hasChallenges"):
            return {"away": a["away"]["remaining"], "home": a["home"]["remaining"]}
    except Exception as e:
        print("abs fetch failed:", repr(e))
    return None


_division = {}  # team id -> (league id, division id), looked up once


def standings(team_id):
    """(division id, [(team id, wins, losses), ...] best first) for the division this team plays in."""
    gc.collect()
    if team_id not in _division:
        d = _get_json("/api/v1/teams/%d?fields=teams,division,id,league" % team_id, 2000)["teams"][0]
        _division[team_id] = (d["league"]["id"], d["division"]["id"])
    league, div = _division[team_id]
    year = time.gmtime(time.time() - 60 * 86400)[0]  # the season runs from spring: before March it is still last year's
    data = _get_json("/api/v1/standings?leagueId=%d&season=%d&standingsTypes=regularSeason"
                     "&fields=records,division,id,teamRecords,team,id,wins,losses,divisionRank,magicNumber,wildCardRank,"
                     "wildCardGamesBack" % (league, year), 30000)
    rows = []
    info = {}  # team id -> (magic number or "", wild card rank or "", games back or "")
    for rec in data["records"]:
        if rec["division"]["id"] == div:
            rows = [(t["team"]["id"], t["wins"], t["losses"]) for t in rec["teamRecords"]]
            for t in rec["teamRecords"]:
                info[t["team"]["id"]] = (str(t.get("magicNumber", "")), str(t.get("wildCardRank", "")),
                                         str(t.get("wildCardGamesBack", "")))
            break
    data = None
    gc.collect()
    return div, rows, info


def fetch(team_ids):
    """Games for one team (or a list of teams) from yesterday through the next week."""
    gc.collect()
    if isinstance(team_ids, int):
        team_ids = [team_ids]
    now = time.time()
    path = ("/api/v1/schedule?sportId=1&teamId=%s&startDate=%s&endDate=%s"
            "&hydrate=linescore,team&fields=%s"
            % (",".join(str(t) for t in team_ids), _day(now - 86400), _day(now + 7 * 86400), FIELDS))
    data = _get_json(path)
    games = []
    seen = set()
    for day in data.get("dates", []):
        for raw in day.get("games", []):
            if raw["gamePk"] in seen:  # two followed teams in one game
                continue
            seen.add(raw["gamePk"])
            g = convert(raw)
            if g:
                games.append(g)
    for g in games:
        if g["state"] == "in" and g["period"]:
            g["abs"] = abs_challenges(g["pk"])
    gc.collect()
    return games


def fetch_all():
    """Every MLB game from last night through today (for the ticker and playoff games not ours)."""
    gc.collect()
    now = time.time()
    path = ("/api/v1/schedule?sportId=1&startDate=%s&endDate=%s&hydrate=linescore,team&fields=%s"
            % (_day(now - 14 * 3600), _day(now), FIELDS))
    data = _get_json(path)
    games = []
    for day in data.get("dates", []):
        for raw in day.get("games", []):
            g = convert(raw)
            if g:
                games.append(g)
    data = None
    live = [g for g in games if g["state"] == "in" and g["period"] and g["playoff"]]
    for g in live[:2]:  # ABS challenges for the playoff games that get a place on the board
        g["abs"] = abs_challenges(g["pk"])
    gc.collect()
    return games
