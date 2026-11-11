# Live hockey extras: shots on goal and power play for a game in progress.
# ESPN's scoreboard has neither, so for each live followed game we read two small things over plain HTTP:
# the top of the game summary (shots and power-play chances per team, only ~3KB of its 300KB) and the
# game's "situation" (is a power play on right now, 340 bytes).
import gc
import time

import espn
import settings

CORE = "sports.core.api.espn.com"
SUMMARY = "/apis/site/v2/sports/hockey/nhl/summary?event=%s"
SITUATION = "/v2/sports/hockey/leagues/nhl/events/%s/competitions/%s/situation"
_chances = {}   # game id -> (away, home) power-play chances seen at the last look
_side = {}      # game id -> which team was last given a power play
_goalies = {}   # game id -> (ticks_ms when looked up, {team abbreviation: goalie's last name})
GOALIE_EVERY = 120000   # the goalie rarely changes, and finding him means reading ~30KB: ask every 2 minutes
GOALIE_LIMIT = 70000    # give up after this many bytes


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


class GoalieScan:
    """Finds each team's goalie in the stream of a game summary, a chunk at a time (the list of
    players is ~25KB into the page). Feed chunks to add(); `done` says when both teams have one."""

    def __init__(self):
        self.buf = b""
        self.started = False
        self.team = None
        self.names = {}
        self.read = 0
        self.found_at = 0
        self.pos = 0   # where in buf the unprocessed part starts

    @property
    def done(self):
        return (len(self.names) >= 2 and self.read - self.found_at > 1500) or self.read > GOALIE_LIMIT

    def add(self, chunk):
        self.read += len(chunk)
        buf = self.buf + chunk
        if not self.started:
            i = buf.find(b'"players":[')
            if i < 0:
                self.buf = buf[-16:]
                return
            self.started = True
            buf = buf[i:]
            self.pos = 0
        pos = self.pos
        hold = len(buf)  # where an unfinished marker starts: keep everything from there
        while True:
            t = buf.find(b'"team":{"id":"', pos)
            g = buf.find(b'"abbreviation":"G"', pos)
            if t < 0 and g < 0:
                break
            if t >= 0 and (g < 0 or t < g):
                a = buf.find(b'"abbreviation":"', t)
                e = buf.find(b'"', a + 16) if a >= 0 else -1
                if a < 0 or e < 0 or a - t > 400:
                    hold = t   # the team's abbreviation hasn't arrived yet
                    break
                self.team = buf[a + 16:e].decode()
                pos = e
            else:
                n = buf.rfind(b'"lastName":"', 0, g)
                if n >= 0 and g - n < 1500 and self.team:
                    self.names[self.team] = espn.last_name(buf[n + 12:buf.find(b'"', n + 12)].decode())
                    self.found_at = self.read
                pos = g + 18
        cut = max(0, min(hold, len(buf) - 1500))   # keep enough behind to find a goalie's name after his position
        self.buf = buf[cut:]
        self.pos = max(0, min(pos, hold) - cut)


def read_goalies(eid):
    """{team abbreviation: goalie last name} from the game summary (the newest goalie listed for each team)."""
    scan = GoalieScan()
    conn, body = espn._open(espn.HOST, SUMMARY % eid)
    try:
        scan.add(body)
        while not scan.done:
            d = conn.read(1024)
            if not d:
                break
            scan.add(d)
    finally:
        conn.close()
    return scan.names


def goalies_for(game):
    """The game's goalies, looked up at most every GOALIE_EVERY ms."""
    eid = game["id"]
    old = _goalies.get(eid)
    now = time.ticks_ms()
    if old and time.ticks_diff(now, old[0]) < GOALIE_EVERY:
        return old[1]
    gc.collect()
    names = read_goalies(eid)
    _goalies[eid] = (now, names)
    return names


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
    try:
        names = goalies_for(game)
        game["goalies"] = {"away": names.get(game["away"], ""), "home": names.get(game["home"], "")}
    except Exception as e:  # shots and power play still show without the goalies
        print("goalies failed:", repr(e))
        settings.log("goalies failed", game["name"], repr(e))
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
