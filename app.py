# Sports scoreboard for Pimoroni Interstate 75 W + 64x32 HUB75 panel.
# Dodgers (MLB), Seahawks (NFL), Kraken (NHL). Scores come from ESPN.
#
# One loop does everything. Network jobs (scores, schedules, weather, clock sync)
# run one at a time, and every wait on the network calls Scoreboard.tick(), which
# draws the next display frame and feeds the watchdog, so the ticker keeps moving
# while something downloads. (A second core for the network was tried: it made
# the display pause for seconds and the connections fail.)
import gc
import json
import os
import random
import time

import machine
import network
import ntptime

import critters
import espn
import interstate75
import jokes
import mlb
import news
import nhl
import ota
import page
import scores
import settings
import teams
import weather
from board import AMBER, FONT, GOLD, GREY, RED, WHITE, Anim, Board, text_width
from scores import (DAYS, LEAGUES, MONTHS, ORIGINAL, SPORT_INDEX, SPORTS, apply_teams, banner, follow_entry, followed, game_key, importance, iso_to_epoch, local_now, make_view,
                    marquee_parts, next_game_lines, next_sun, record_text, result_text, sun_today, visible)
from secrets import WIFI_PASSWORD, WIFI_SSID

log = settings.log

DISPLAY = interstate75.DISPLAY_INTERSTATE75_64X32

POLL_LIVE = 15        # seconds between checks while one of our teams is playing
POLL_SOON = 60        # a game starts within the hour
POLL_IDLE = 300       # nothing happening
NTP_REFRESH = 6 * 3600
NEXT_REFRESH = 30 * 60  # how often to re-read each team's next game
WEATHER_REFRESH = 15 * 60
NEWS_REFRESH = 30 * 60
SLIDE_SECONDS = 6       # idle screen: seconds per slide (clock, then each team)
ALL_REFRESH = 240       # how often to re-read league-wide scores for the ticker
ALL_LIVE = 15           # ...and while a playoff game is on, which also gets a place on the board
IDLE_FRAME_MS = (80, 55, 35, 22)  # ticker scroll speed (1 pixel per frame) for the "speed" setting
CAMEO_MIN = 120         # first cameo after boot comes within CAMEO_MIN seconds
CAMEO_RATES = ((60, 120), (120, 300), (600, 1200), (0, 0))  # seconds between cameos: often, normal, rare, off
CACHE_EVERY = 30 * 60   # how often the schedule/ticker cache is written to flash
BRIGHT_STEPS = (0, 10, 25, 50, 100)  # web page choices; 0 = automatic by time of day
SLIDE_REGION = (0, 24)
TICKER_REGION = (25, 32)
FRAME_MS = 30
SETTING_KEYS = ("display", "mode", "bright", "cameos", "lat", "lon", "tz", "qs", "qe", "sunbright",
                "team_baseball", "team_football", "team_hockey", "team_basketball", "team_soccer", "h24", "news", "logos", "delay", "tickmine", "speed")
MEM_ERRORS_RESTART = 10  # restart (when idle) after this many MemoryErrors: the heap is too fragmented
WIPE_FRAMES = 6  # frames a new idle slide takes to wipe in from the left
STANDINGS_REFRESH = 30 * 60  # seconds between division table downloads
DIVISIONS = {200: "AL WEST", 201: "AL EAST", 202: "AL CENTRAL", 203: "NL WEST", 204: "NL EAST", 205: "NL CENTRAL"}
MODES = ("NORMAL", "CLOCK", "ART")  # button B cycles these; button A plays a cameo now
WDT_MS = 8000           # hardware watchdog: reboot if the display loop stalls this long
STALE_MS = 15 * 60 * 1000  # reboot if the network worker delivers nothing for this long
STALE_DATA_MS = 120 * 1000  # a live game's score older than this gets the amber status pixel
MEM_LOG_EVERY = 30 * 60 * 1000  # free memory goes in the log this often (a slow leak shows up as a trend)
RESTART_HOUR = 4        # a restart at 4 AM local, when nothing is on screen, clears memory fragmentation
RESTART_AFTER = 6 * 3600  # ...but only if the board has been up at least this long
CLOSE_MS = 450          # close games redraw this often so the corner lights pulse


i75 = interstate75.Interstate75(display=DISPLAY)
board = Board(i75.display, i75.width, i75.height)
wlan = network.WLAN(network.STA_IF)


_wdt = None  # set in main(); create a file named `nowdt` on the board to turn it off while developing


def feed():
    if _wdt:
        _wdt.feed()


def message(*lines):
    board.draw_message(list(lines))
    i75.update()


def _networks():
    """The WiFi networks to try. A second one (WIFI_SSID2/WIFI_PASSWORD2 in secrets.py) is optional."""
    nets = [(WIFI_SSID, WIFI_PASSWORD)]
    try:
        from secrets import WIFI_PASSWORD2, WIFI_SSID2
        nets.append((WIFI_SSID2, WIFI_PASSWORD2))
    except ImportError:
        pass
    return nets


_net = 0  # which network connected last; it is tried first next time


def wifi_up(timeout=20):
    global _net
    wlan.active(True)
    try:
        network.hostname("scoreboard")  # reachable as scoreboard.local
    except Exception:
        pass
    if wlan.isconnected():
        return True
    nets = _networks()
    for k in range(len(nets)):
        i = (_net + k) % len(nets)
        wlan.connect(nets[i][0], nets[i][1])
        t0 = time.ticks_ms()
        while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t0) < timeout * 1000:
            feed()
            espn._wait()  # keeps the display moving once the main loop is running
        if wlan.isconnected():
            if k:
                log("wifi: connected to", nets[i][0])
            _net = i
            return True
        try:
            wlan.disconnect()
        except OSError:
            pass
    return False


def sync_clock():
    for _ in range(3):
        try:
            ntptime.settime()
            return True
        except OSError:
            feed()
            time.sleep(1)
    return False


def unquote(s):
    """%XX and + in text from a web address."""
    s = s.replace("+", " ")
    out = bytearray()
    i = 0
    while i < len(s):
        if s[i] == "%" and len(s) - i >= 3:
            try:
                out.append(int(s[i + 1:i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out += s[i].encode()
        i += 1
    return out.decode()


def brightness_for(hour, now=None):
    """0 = dark. Quiet hours and the display switch turn the panel off; otherwise a fixed level from the web
    page, or automatic: full in daylight, dimmer from an hour before sunset, dim overnight (clock hours
    when the sun times are off or unknown). `now` is the epoch time, for the sun."""
    if not settings.cfg["display"]:
        return 0.0
    if now is not None and settings.quiet_now(hour):
        return 0.0
    fixed = settings.cfg["bright"]
    if fixed:
        return fixed / 100
    if now is not None and settings.cfg["sunbright"]:
        rise, sset = sun_today(now)
        if rise and sset:
            if rise + 1800 <= now < sset - 3600:
                return 1.0
            if rise - 1800 <= now < sset + 3600:
                return 0.6
            return 0.25
    if 7 <= hour < 19:
        return 1.0
    if 19 <= hour < 22 or 6 <= hour < 7:
        return 0.6
    return 0.25


def sky_for(hour):
    """Colour behind daytime cameos: blue by day, a warm tint at dawn and dusk, black at night."""
    if 8 <= hour < 18:
        return (0, 18, 45)
    if 5 <= hour < 8 or 18 <= hour < 20:
        return (40, 14, 38)
    return None


# -- network worker (runs on core 1) -------------------------------------
def job_poll(i):
    """Scores for every team we follow in sport i."""
    sport = SPORTS[i]
    follows = [f for f in LEAGUES if f["sport"] == sport["sport"]]
    if not wifi_up():
        raise OSError("wifi")
    if sport["sport"] == "baseball":
        games = mlb.fetch([f["mlb_team_id"] for f in follows])
    else:
        games = espn.fetch(sport["sport"], sport["path"], tuple(f["abbr"] for f in follows),
                           sport["early_exit"] and len(follows) == 1)  # stop early only when one game is wanted
        if sport["sport"] == "hockey":
            nhl.add_live(games)  # shots on goal and power play for live games
    now = time.time()
    if any(g["state"] == "in" for g in games):
        wait = POLL_LIVE
    elif any(g["state"] == "pre" and 0 <= iso_to_epoch(g["date"]) - now < 3600 for g in games):
        wait = POLL_SOON
    else:
        wait = POLL_IDLE
    print("poll", sport["sport"], [(g["name"], g["state"], g["away_score"], g["home_score"]) for g in games])
    return games, wait


def job_next(i):
    """One followed team's next game; i is (sport, abbreviation)."""
    league = follow_entry(*i)
    if league is None:
        raise OSError("not followed any more")
    if not wifi_up():
        raise OSError("wifi")
    nx = espn.next_event(league["path"], league["team_slug"])
    print("next", league["nick"], nx)
    return nx, NEXT_REFRESH


def job_standings(i):
    """The division table for one followed baseball team; i is (sport, abbreviation)."""
    league = follow_entry(*i)
    if league is None or league["sport"] != "baseball":
        raise OSError("not followed any more")
    if not wifi_up():
        raise OSError("wifi")
    row = [r for r in teams.TEAMS["baseball"] if r[2] == league["abbr"]]
    if not row:
        raise OSError("unknown team")
    div, rows, info = mlb.standings(row[0][5])
    names = {r[5]: r[2] for r in teams.TEAMS["baseball"]}
    race = {names.get(t, "?"): v for t, v in info.items()}  # abbreviation -> (magic number, wild card rank, games back)
    return (div, [(names.get(t, "?"), w, l) for t, w, l in rows], race), STANDINGS_REFRESH


def job_all(i):
    """League-wide scoreboard for the idle ticker (every team, not just ours)."""
    sport = SPORTS[i]
    if not wifi_up():
        raise OSError("wifi")
    if sport["sport"] == "baseball":  # ESPN has no runners/outs/count; MLB does
        games = mlb.fetch_all()
    else:
        games = espn.fetch(sport["sport"], sport["path"], None, False)
    print("league", sport["sport"], len(games), "games")
    live = any(g["state"] == "in" and importance(g) for g in games)
    return games, ALL_LIVE if live else ALL_REFRESH


def job_weather(_):
    if not wifi_up():
        raise OSError("wifi")
    wx = weather.fetch(settings.cfg["lat"], settings.cfg["lon"])
    print("weather", wx)
    return wx, WEATHER_REFRESH


def job_news(i):
    """Headlines for sport i, for the idle ticker (only the sports we follow, and only when switched on)."""
    sport = SPORTS[i]
    if not settings.cfg["news"] or not any(f["sport"] == sport["sport"] for f in LEAGUES):
        return [], NEWS_REFRESH
    if not wifi_up():
        raise OSError("wifi")
    heads = news.fetch(sport["path"])
    print("news", sport["nick"], len(heads))
    return heads, NEWS_REFRESH


def clock_text(secs):
    """3725 -> '1:02:05', 65 -> '1:05'."""
    if secs >= 3600:
        return "%d:%02d:%02d" % (secs // 3600, secs // 60 % 60, secs % 60)
    return "%d:%02d" % (secs // 60, secs % 60)


def job_ntp(_):
    if not wifi_up() or not sync_clock():
        raise OSError("ntp")
    return True, NTP_REFRESH


JOBS = {"poll": job_poll, "next": job_next, "stand": job_standings, "all": job_all, "wx": job_weather, "news": job_news, "ntp": job_ntp}
PRIORITY = {"poll": 0, "all": 1, "next": 2, "stand": 3, "wx": 3, "news": 3, "ntp": 3}  # live scores before the ticker's league-wide data


class Scoreboard:
    def __init__(self):
        self.inbox = []      # finished network jobs, applied by drain()
        self.due = {}        # (job kind, sport index; or (sport, abbreviation) for "next") -> ticks_ms when it is next due
        self.data = {}       # sport index -> games of the teams we follow, from the last good poll
        self.mem_errors = 0   # downloads that failed for lack of one big block of memory (heap fragmentation)
        self.prev_idx = None  # the idle slide shown last frame (a change starts a wipe)
        self.wipe = 0
        self.standings = {}  # (sport, abbreviation) -> (division id, [(abbr, wins, losses)]) for followed baseball teams
        self.upcoming = {}   # (sport, abbreviation) -> that team's next scheduled game (for the idle screen)
        self.slide = -1
        self.slide_drawn = None  # which slide is on screen (None = redraw it)
        self.all_games = {}  # sport index -> every game in that sport's scoreboard
        self.weather = None  # (icon kind, "54F")
        self.news = {}       # sport index -> headlines for the ticker
        self.ticker = []
        self.ticker_width = 0
        self.ticker_stale = True
        self.joke = None
        self.offset = 0
        self.last_refresh = 0
        self.scores = {}     # game key -> (away, home) last seen
        self.states = {}     # game key -> pre / in / post
        self.ended = {}      # game key -> epoch when we saw it finish (a final score stays up an hour after)
        self.anims = []      # queued/active animations
        self.held = {}       # (job kind, sport index) -> [release ticks_ms, finished job] while the spoiler delay holds it
        self.timer_end = None  # ticks_ms when the timer rings
        self.timer_over = None  # ticks_ms when it rang ("TIME'S UP" shows for a minute)
        self.stopwatch = None  # [started ticks_ms, or None when paused, seconds counted before the pause]
        self.clocks = {}     # game key -> [(clock, period), ticks_ms first seen, running?] to count the game clock down between reads
        self.ticking = False
        self.views = []
        self.shown = []
        self.clock_ok = False
        self.dirty = True
        self.last_draw = 0
        self.cameo = None
        self.cameo_due = time.ticks_add(time.ticks_ms(), random.randint(60, CAMEO_MIN) * 1000)
        self.mode = settings.cfg["mode"]
        scores.H24 = bool(settings.cfg["h24"])
        self.buttons = (False, False)
        self.look_due = 0
        self.last_result = time.ticks_ms()  # when a network job last succeeded
        self.ota = None
        self.ota_next = 0
        self.healthy_due = time.ticks_add(time.ticks_ms(), 90000)
        self.next_frame = time.ticks_ms()
        self.job = "-"       # the network job in progress (for stall reports)
        self.worst_gap = 0   # how late the display has been for a frame, since the last report
        self.report_due = time.ticks_add(time.ticks_ms(), 60000)
        self.team_gen = [0] * len(SPORTS)  # bumps when the teams followed in a sport change, so old results are dropped
        self.fails = {}      # (job kind, league) -> failures in a row, for the status pixel
        self.net_ok = True
        self.net_check = 0
        self.fresh = {}      # sport index -> ticks_ms of the last good score read (poll or league-wide)
        self.boot_epoch = None  # time.time() once the clock is right, for the daily restart
        self.mem_due = time.ticks_add(time.ticks_ms(), MEM_LOG_EVERY)
        self.cache_due = time.ticks_add(time.ticks_ms(), 5 * 60000)

    # -- finished network jobs ---------------------------------------------
    def drain(self):
        now = time.ticks_ms()
        delay = settings.cfg["delay"]
        for k in list(self.held):  # scores held back for the spoiler delay
            due, item = self.held[k]
            if not delay or time.ticks_diff(now, due) >= 0:
                del self.held[k]
                self.apply(*item)
        while self.inbox:
            self.last_result = time.ticks_ms()
            kind, i, ok, value = self.inbox.pop(0)
            if kind in ("poll", "all"):
                self.fresh[i] = self.last_result
                have = self.data.get(i) if kind == "poll" else self.all_games.get(i)
                if delay and have is not None:  # hold it back; a newer read replaces it but keeps the original release time
                    k = (kind, i)
                    if k in self.held:
                        self.held[k][1] = (kind, i, ok, value)
                    else:
                        self.held[k] = [time.ticks_add(self.last_result, delay * 1000), (kind, i, ok, value)]
                    continue
            self.apply(kind, i, ok, value)

    def apply(self, kind, i, ok, value):
        if kind == "poll":
            self.note_clocks(SPORTS[i], value)
            self.detect_changes(SPORTS[i], value)
            self.data[i] = value
            self.refresh_views()
        elif kind == "next":
            self.upcoming[i] = value
        elif kind == "stand":
            self.standings[i] = value
        elif kind == "all":
            self.note_clocks(SPORTS[i], value)
            self.detect_changes(SPORTS[i], [g for g in value if importance(g)])
            self.all_games[i] = value
            self.refresh_views()
            self.ticker_stale = True
        elif kind == "wx":
            self.weather = value
        elif kind == "news":
            self.news[i] = value
            self.ticker_stale = True
        elif kind == "ntp":
            self.clock_ok = True
            if self.boot_epoch is None:
                self.boot_epoch = time.time()
        self.dirty = True

    def detect_changes(self, league, games):
        """Score changes and game results. `league` only says which sport; each game is judged from the
        side of whichever followed team is in it."""
        sport = league["sport"]
        for g in games:
            key = game_key(sport, g)
            now_scores = (g["away_score"], g["home_score"])
            old = self.scores.get(key)
            old_state = self.states.get(key)
            self.scores[key] = now_scores
            self.states[key] = g["state"]
            if old_state == "in" and g["state"] == "post":
                self.ended[key] = time.time()
                ours = "away" if followed(sport, g["away"]) else "home" if followed(sport, g["home"]) else None
                away_pts, home_pts = now_scores  # (MicroPython can't reverse a tuple with [::-1])
                mine, theirs = (away_pts, home_pts) if ours == "away" else (home_pts, away_pts)
                if ours and mine != theirs:
                    won = mine > theirs
                    self.anims.append(Anim(key, sport, follow_entry(sport, g[ours])["color"], result_text(won, mine, theirs),
                                           True, 150, "win" if won else "loss"))
            if old is None or g["state"] == "pre":
                continue
            if sport == "basketball":
                continue  # baskets come every half minute: no banner for each one (the final result still gets one)
            for side, o, n in (("away", old[0], now_scores[0]), ("home", old[1], now_scores[1])):
                if n > o:
                    text, ours = banner(league, g, side, n - o)
                    a = Anim(key, sport, follow_entry(sport, g[side])["color"] if ours else GREY, text, ours)
                    if ours and (sport, g[side]) in ORIGINAL:  # the celebrations are drawn for those teams
                        a.cameo = critters.scoring(sport, n - o)
                        if a.cameo:
                            a.total = a.cameo.total
                    self.anims.append(a)

    # -- drawing ---------------------------------------------------------
    def note_clocks(self, league, games):
        """Remember when each live game's clock last moved, so it can keep counting between reads."""
        now = time.ticks_ms()
        for g in games:
            if g["state"] != "in" or not g.get("clock"):
                continue
            key = game_key(league["sport"], g)
            c = (g["clock"], g["period"])
            old = self.clocks.get(key)
            if old is None:
                self.clocks[key] = [c, now, False]
            elif old[0] != c:
                self.clocks[key] = [c, now, True]   # it moved since the last read: running
            else:
                old[2] = False                       # same as last read: stopped

    def ticked(self, league, g, now_ms):
        """The game with its clock counted down by the time since it was last read."""
        rec = self.clocks.get(game_key(league["sport"], g))
        if g["state"] != "in" or not rec or not rec[2]:
            return g
        try:
            m, s = rec[0][0].split(":")
            total = int(m) * 60 + int(s)
        except ValueError:  # e.g. "45.3" in the last minute
            return g
        total = max(0, total - min(time.ticks_diff(now_ms, rec[1]) // 1000, 60))
        self.ticking = True
        return dict(g, clock="%d:%02d" % (total // 60, total % 60))

    def refresh_views(self):
        now = time.time()
        pairs = visible([(SPORTS[i], self.data.get(i, [])) for i in range(len(SPORTS))],
                        now, self.clock_ok,
                        [(SPORTS[i], self.all_games.get(i, [])) for i in range(len(SPORTS))], self.ended)
        self.shown = pairs
        self.ticking = False
        now_ms = time.ticks_ms()
        self.views = [make_view(l, self.ticked(l, g, now_ms), now) for l, g in pairs]
        self.last_refresh = time.ticks_ms()

    def build_ticker(self):
        """Scores plus a joke. Rebuilt only when the ticker has scrolled off, so it never jumps."""
        scores = marquee_parts([(SPORTS[i], self.all_games.get(i, [])) for i in range(len(SPORTS))],
                               time.time(), self.clock_ok, bool(settings.cfg["tickmine"]))
        text, color = jokes.next_joke(self.joke)
        self.joke = text
        heads = []
        if settings.cfg["news"]:
            for i in sorted(self.news):
                for h in self.news[i]:
                    heads += [("|", (90, 90, 90)), (h, (150, 200, 255))]
        fresh = scores + heads + [("|", (90, 90, 90)), (text, color), ("|", (90, 90, 90))]
        # append to what is still on screen so there is never a black gap after a joke
        x = board.w - self.offset
        keep = []
        for part in self.ticker:
            x += text_width(part[0]) + 4
            if x > 0:
                keep.append(part)
            else:
                self.offset -= text_width(part[0]) + 4
        self.ticker = keep + fresh
        self.ticker_width = board.marquee_width(self.ticker)
        self.ticker_stale = False

    def region_for(self, key):
        n = len(self.shown)
        for idx, (l, g) in enumerate(self.shown):
            if game_key(l["sport"], g) == key:
                return board.regions(n)[idx]
        return None

    def idle_screen(self):
        """No games on: clock or a team's next game on top (rotating), scores and jokes scrolling below."""
        lines = self.timer_lines()
        if lines:  # a running timer or stopwatch takes the top of the idle screen
            key = ("timer", repr(lines))
            if self.slide_drawn != key:
                board.draw_message(lines, SLIDE_REGION)
                board.rect(0, SLIDE_REGION[1], board.w, 1, (35, 35, 35))
                self.slide_drawn = key
            self.prev_idx = None
            board.draw_marquee(self.ticker, self.offset, TICKER_REGION)
            return
        now = time.time()
        n = len(LEAGUES)
        lt = local_now(now)
        extra = self.extra_slides(lt) if self.clock_ok else []
        idx = 0 if self.mode == 1 else self.slide % (n + 2 + len(extra))  # 0 is the clock, then the teams, the sun, the extras
        if idx == 0:
            fx = self.weather[0] if self.weather else None
            moving = fx in ("rain", "snow", "storm")
            key = (idx, lt[4], self.offset // 2 if moving else 0)
            if self.slide_drawn != key:
                h = lt[3]
                hhmm = "%d:%02d" % (h if scores.H24 else h % 12 or 12, lt[4])
                date = "%s %s %d" % (DAYS[lt[6]], MONTHS[lt[1] - 1], lt[2])
                board.draw_clock(SLIDE_REGION, hhmm, "" if scores.H24 else "A" if h < 12 else "P", date, self.weather, self.offset)
                board.rect(0, SLIDE_REGION[1], board.w, 1, (35, 35, 35))
                self.slide_drawn = key
        elif idx == n + 1:  # next sunrise or sunset
            if self.slide_drawn != (idx, lt[4]):
                sun = next_sun(now) if self.clock_ok else None
                if sun:
                    name, at, mins = sun
                    left = "IN %d MIN" % mins if mins < 60 else "IN %dH %02dM" % (mins // 60, mins % 60)
                    lines = [(name, GREY), (at, AMBER), (left, WHITE)]
                else:
                    lines = [("SUN", GREY), ("NO DATA", GREY)]
                board.draw_message(lines, SLIDE_REGION)
                board.rect(0, SLIDE_REGION[1], board.w, 1, (35, 35, 35))
                self.slide_drawn = (idx, lt[4])
        elif idx > n + 1:  # division standings, countdowns and reminders
            lines = extra[idx - n - 2]
            key = (idx, repr(lines))
            if self.slide_drawn != key:
                board.draw_message(lines, SLIDE_REGION)
                board.rect(0, SLIDE_REGION[1], board.w, 1, (35, 35, 35))
                self.slide_drawn = key
        elif self.slide_drawn != idx:  # team slides only change every few seconds
            i = idx - 1
            league = LEAGUES[i]
            lines = [(league["nick"], league["color"])]
            nx = self.upcoming.get((league["sport"], league["abbr"]))
            if nx and (not self.clock_ok or iso_to_epoch(nx["date"]) > now - 3600):
                rec = record_text(nx)
                if rec and text_width(league["nick"] + " " + rec) <= board.w - 2:
                    lines = [([(league["nick"], league["color"]), (rec, GREY)], WHITE)]
                colors = {"opp": WHITE, "rival": GOLD, "when": AMBER}
                lines += [(t, colors[role]) for t, role in next_game_lines(league, nx, now)]
            else:
                lines += [("NOTHING", GREY), ("SCHEDULED", GREY)]
            board.draw_message(lines, SLIDE_REGION)
            board.rect(0, SLIDE_REGION[1], board.w, 1, (35, 35, 35))
            self.slide_drawn = idx
        if idx != self.prev_idx:
            if self.prev_idx is not None:
                self.wipe = WIPE_FRAMES
            self.prev_idx = idx
        if self.wipe:  # a new slide: reveal it from the left, the rest still black; redraw next frame
            x = (WIPE_FRAMES + 1 - self.wipe) * board.w // WIPE_FRAMES
            if x < board.w:
                board.rect(x, 0, board.w - x, SLIDE_REGION[1], (0, 0, 0))
            self.wipe -= 1
            self.slide_drawn = None
        board.draw_marquee(self.ticker, self.offset, TICKER_REGION)

    def timer_lines(self):
        """What the timer or stopwatch shows, or None when neither is running."""
        now = time.ticks_ms()
        if self.timer_end is not None:
            left = time.ticks_diff(self.timer_end, now) // 1000
            if left > 0:
                return [("TIMER", GREY), (clock_text(left), AMBER if left > 10 else GOLD)]
            self.timer_over = self.timer_end
            self.timer_end = None
        if self.timer_over is not None:
            if time.ticks_diff(now, self.timer_over) < 60000:
                flash = (time.ticks_diff(now, self.timer_over) // 500) % 2
                return [("TIME'S UP!", GOLD if flash else WHITE), ("TIMER DONE", GREY)]
            self.timer_over = None
        if self.stopwatch is not None:
            started, before = self.stopwatch
            secs = before + (time.ticks_diff(now, started) // 1000 if started is not None else 0)
            return [("STOPWATCH" if started is not None else "PAUSED", GREY), (clock_text(secs), WHITE)]
        return None

    def set_timer(self, q):
        """?timer=SECONDS starts a countdown (0 cancels); ?stopwatch=1 starts or resumes, 0 pauses, clear removes."""
        if "timer" in q:
            secs = int(q["timer"]) if q["timer"].isdigit() else 0
            secs = min(secs, 24 * 3600)
            self.timer_over = None
            self.timer_end = time.ticks_add(time.ticks_ms(), secs * 1000) if secs else None
        if "stopwatch" in q:
            v, now = q["stopwatch"], time.ticks_ms()
            if v == "clear":
                self.stopwatch = None
            elif v == "1":
                if self.stopwatch is None:
                    self.stopwatch = [now, 0]
                elif self.stopwatch[0] is None:
                    self.stopwatch[0] = now
            elif v == "0" and self.stopwatch is not None and self.stopwatch[0] is not None:
                self.stopwatch = [None, self.stopwatch[1] + time.ticks_diff(now, self.stopwatch[0]) // 1000]
        self.slide_drawn = None
        self.dirty = True

    def extra_slides(self, lt):
        """Lines for the slides after the sun: division tables, then countdowns and reminders."""
        out = []
        seen = []
        for league in LEAGUES:
            st = self.standings.get((league["sport"], league["abbr"]))
            if not st or st[0] in seen or not st[1]:
                continue
            seen.append(st[0])
            mine = [f["abbr"] for f in LEAGUES if f["sport"] == "baseball"]
            rows = []
            for rank, (ab, w, l) in enumerate(st[1], 1):
                color = WHITE  # (next() with a default does not work on the board)
                for f in LEAGUES:
                    if f["sport"] == "baseball" and f["abbr"] == ab:
                        color = f["color"]
                rows.append(([(str(rank), GREY), (ab, color), ("%d-%d" % (w, l), WHITE if ab in mine else GREY)], WHITE))
            out.append(rows[:3])
            race = st[2] if len(st) > 2 else {}
            for f in LEAGUES:  # magic number (division leader) or wild card position, from the same standings read
                if f["sport"] != "baseball" or f["abbr"] not in race:
                    continue
                magic, wc_rank, wc_back = race[f["abbr"]]
                if magic.isdigit() and magic != "0":
                    out.append([(f["abbr"], f["color"]), ("MAGIC NUMBER", GREY), (magic, GOLD)])
                elif wc_rank.isdigit() and wc_rank != "0":
                    out.append([(f["abbr"], f["color"]), ("WILD CARD " + wc_rank, GREY), (wc_back[1:] + " AHEAD" if wc_back.startswith("+") else wc_back + " GB" if wc_back not in ("", "-") else "", AMBER)])
            if len(rows) > 3:
                out.append([(DIVISIONS.get(st[0], "DIVISION"), GREY)] + rows[3:5])
        for text, days in settings.active_reminders(lt):
            if days is None:
                head = [("REMINDER", GOLD)]
            else:
                head = [("TODAY!" if days == 0 else "%d DAY%s TO" % (days, "" if days == 1 else "S"), AMBER)]
            lines, cur = head, ""
            for w in text.split():
                if cur and text_width(cur + " " + w) > board.w - 2:
                    lines.append((cur, WHITE))
                    cur = w
                else:
                    cur = (cur + " " + w) if cur else w
            lines.append((cur, WHITE))
            out.append(lines[:3])
        return out

    def data_stale(self, now):
        """True when a live game on screen has not had a good score read for STALE_DATA_MS."""
        for league, g in self.shown:
            if g["state"] == "in":
                t = self.fresh.get(SPORT_INDEX[league["sport"]])
                if t is not None and time.ticks_diff(now, t) > STALE_DATA_MS:
                    return True
        return False

    def pulse(self):
        """Gold corner lights, blinking, while a game on screen is close and late."""
        if time.ticks_ms() // 500 % 2 and any(v.get("close") for v in self.views):
            board._clip = (0, board.h)
            for x, y, dx, dy in ((0, 0, 1, 1), (board.w - 1, 0, -1, 1), (0, board.h - 1, 1, -1),
                                 (board.w - 1, board.h - 1, -1, -1)):
                for px, py in ((x, y), (x + dx, y), (x, y + dy)):
                    board.rect(px, py, 1, 1, GOLD)

    def flush(self):
        """Show the frame, with one pixel in the top right corner when something is wrong:
        red = no WiFi, amber = a data source keeps failing or a live score is stale."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.net_check) >= 0:
            self.net_ok = wlan.isconnected()
            self.net_check = time.ticks_add(now, 2000)
        bad = RED if not self.net_ok else AMBER if (
            any(n >= 3 for n in self.fails.values()) or self.data_stale(now)) else None
        if bad:
            board._clip = (0, board.h)
            board.rect(board.w - 1, 0, 1, 1, bad)
        i75.update()

    def draw(self):
        if self.anims:
            a = self.anims[0]
            region = self.region_for(a.key)
            if a.cameo:  # our team scored: a whole-panel celebration
                self.slide_drawn = None
                hour = local_now(time.time())[3] if self.clock_ok else 12
                a.cameo.draw(board, sky_for(hour))
                a.frame += 1
                if a.cameo.done or a.done:
                    self.anims.pop(0)
                    self.dirty = True
                self.flush()
                self.last_draw = time.ticks_ms()
                return
            if region is None:  # game scrolled off the board; skip its animation
                self.anims.pop(0)
                return self.draw()
            self.slide_drawn = None
            board.draw_games(self.views)
            board.draw_anim(a, region)
            a.frame += 1
            if a.done:
                self.anims.pop(0)
                self.dirty = True
        elif self.views:
            self.cameo = None
            self.slide_drawn = None
            board.draw_games(self.views)
            self.pulse()
        elif self.cameo:
            self.slide_drawn = None  # a cameo repaints the whole panel
            hour = local_now(time.time())[3] if self.clock_ok else 12
            self.cameo.draw(board, sky_for(hour))
            if self.cameo.done:
                self.cameo = None
                critters.release()  # frees the memory of an extra cameo's file
        else:
            self.idle_screen()
        self.flush()
        self.last_draw = time.ticks_ms()

    # -- buttons, night mode, cameos -----------------------------------
    def start_cameo(self, name=None):
        lt = local_now(time.time())
        self.cameo = (name and critters.make(name)) or critters.pick(
            lt[1], lt[2], [(l["sport"], l["abbr"]) for l in LEAGUES])
        lo, hi = CAMEO_RATES[settings.cfg["cameos"]]
        wait = random.randint(lo, hi) if hi else 3600  # "off" still checks back every hour
        self.cameo_due = time.ticks_add(time.ticks_ms(), wait * 1000)

    def check_buttons(self):
        try:
            now = (i75.switch_pressed(interstate75.SWITCH_A), i75.switch_pressed(interstate75.SWITCH_B))
        except Exception:
            return
        a, b = (n and not p for n, p in zip(now, self.buttons))
        self.buttons = now
        if a and not self.views:
            self.start_cameo()
        if b:
            self.mode = (self.mode + 1) % len(MODES)
            settings.cfg["mode"] = self.mode
            settings.save()
            self.slide_drawn = None
            self.cameo = None
            message(("MODE", GREY), (MODES[self.mode], AMBER))
            time.sleep_ms(700)

    def look(self):
        """Once in a while: brightness for the time of day."""
        if (self.clock_ok or settings.cfg["bright"] or not settings.cfg["display"]) and time.ticks_diff(time.ticks_ms(), self.look_due) >= 0:
            now = time.time() if self.clock_ok else None
            board.set_brightness(brightness_for(local_now(now)[3] if now else 12, now))
            self.slide_drawn = None
            self.look_due = time.ticks_add(time.ticks_ms(), 60000)

    def watch(self, now_ms):
        """Report the worst display stall; reboot if the network has been silent too long."""
        if time.ticks_diff(now_ms, self.report_due) >= 0:
            print("display: worst frame delay", self.worst_gap, "ms; free", gc.mem_free())
            self.worst_gap = 0
            self.report_due = time.ticks_add(now_ms, 60000)
        if time.ticks_diff(now_ms, self.mem_due) >= 0:
            gc.collect()
            log("mem free", gc.mem_free() // 1024, "KB")
            self.mem_due = time.ticks_add(now_ms, MEM_LOG_EVERY)
        if (self.boot_epoch and not self.views and not self.anims and not _wdt_off()
                and time.time() - self.boot_epoch > RESTART_AFTER and local_now(time.time())[3] == RESTART_HOUR):
            log("daily restart")
            settings.save_log()
            machine.reset()
        if (self.mem_errors >= MEM_ERRORS_RESTART and self.boot_epoch and not self.views and not self.anims
                and not self.cameo and not _wdt_off() and time.time() - self.boot_epoch > 600):
            log("memory fragmented (%d allocation failures); restarting" % self.mem_errors)  # a fresh heap fixes it
            settings.save_log()
            machine.reset()
        if time.ticks_diff(now_ms, self.last_result) > STALE_MS and not _wdt_off():
            log("no network results for 15 min; rebooting")
            settings.save_log()
            machine.reset()

    # -- cache -------------------------------------------------------------
    def save_cache(self):
        """Write what the idle screen needs to flash (never while a game is on: the write can pause the display)."""
        if self.views and not self.anims:
            self.cache_due = time.ticks_add(time.ticks_ms(), 60000)
            return
        self.cache_due = time.ticks_add(time.ticks_ms(), CACHE_EVERY * 1000)
        if not self.clock_ok or not (self.upcoming or self.all_games):
            return
        settings.save_cache({
            "t": int(time.time()),
            "teams": ["%s:%s" % (l["sport"], l["abbr"]) for l in LEAGUES],
            "up": {"%s:%s" % k: v for k, v in self.upcoming.items()},
            "wx": self.weather,
            "all": {str(i): [g for g in v if g["state"] != "in"] for i, v in self.all_games.items()},
        })

    def load_cache(self):
        """After a restart: fill the idle screen with the last known schedule until fresh data arrives."""
        c = settings.load_cache()
        if not c or not self.clock_ok or abs(time.time() - c.get("t", 0)) > 6 * 3600:
            return
        try:
            if c.get("teams") != ["%s:%s" % (l["sport"], l["abbr"]) for l in LEAGUES]:  # saved for other teams
                return
            self.upcoming = {tuple(k.split(":")): v for k, v in c.get("up", {}).items()}
            self.all_games = {int(i): v for i, v in c.get("all", {}).items()}
            wx = c.get("wx")
            self.weather = (wx[0], wx[1]) if wx else None
            self.ticker_stale = True
            log("cache loaded")
        except Exception as e:
            self.upcoming, self.all_games, self.weather = {}, {}, None
            log("cache ignored:", repr(e))

    # -- web page ----------------------------------------------------------
    def web(self, method, path, q):
        """Handler for ota.py: the settings page (/ui), its data (/state), changes (/set) and the log."""
        if path == "/log":
            return 200, settings.read_log(), "text/plain"
        if path == "/state":
            d = dict(settings.cfg)
            d["info"] = "%s - %d games on screen - %d KB free" % (
                "WiFi ok" if self.net_ok else "NO WIFI", len(self.views), gc.mem_free() // 1024)
            return 200, json.dumps(d), "application/json"
        if path == "/teams":  # the choices for one league: [[abbreviation, full name], ...]
            return 200, json.dumps([[r[2], r[0]] for r in teams.TEAMS.get(q.get("sport"), ())]), "application/json"
        if path == "/export":  # the settings as a file, to keep or to paste into /import after a reflash
            return 200, json.dumps(settings.cfg), "application/json"
        if path == "/reminders":
            return 200, json.dumps(settings.reminders), "application/json"
        if path == "/rem_add":
            try:
                settings.add_reminder(unquote(q.get("text", "")), q.get("date", ""), unquote(q.get("time", "")), q.get("rep", 0))
            except (ValueError, TypeError):
                return 400, "not valid (10 at most, needs text and a date)", "text/plain"
            self.slide_drawn = None
            return 200, "ok", "text/plain"
        if path == "/rem_del":
            ok = settings.delete_reminder(int(q["i"]) if q.get("i", "").isdigit() else -1)
            self.slide_drawn = None
            return (200, "ok", "text/plain") if ok else (400, "no such reminder", "text/plain")
        if path not in ("/", "/ui", "/set", "/import"):
            return None
        changed = False
        if path == "/import":
            n = settings.import_json(unquote(q.get("json", "")))
            q = dict(settings.cfg, **{k: v for k, v in q.items() if k == "k"})  # apply everything below
            if not n:
                return 400, "nothing imported", "text/plain"
            changed = True
        for key in SETTING_KEYS:
            if key in q and settings.set_value(key, q[key]):
                changed = True
        if changed:
            settings.save()
            self.mode = settings.cfg["mode"]
            scores.H24 = bool(settings.cfg["h24"])
            self.slide_drawn = None
            self.look_due = 0  # apply brightness now
            if "lat" in q or "lon" in q:
                self.due[("wx", 0)] = time.ticks_ms()  # weather for the new place
            if "mode" in q:
                self.cameo = None
            if "news" in q:
                self.ticker_stale = True
                for k in list(self.due):
                    if k[0] == "news":
                        self.due[k] = time.ticks_ms()
            self.follow()
        if "timer" in q or "stopwatch" in q:
            self.set_timer(q)
        if "cameo" in q and not self.views:
            self.start_cameo(q["cameo"] if q["cameo"].isalpha() else None)  # ?cameo=1 plays any; ?cameo=Rocket that one
        if q.get("msg"):
            self.say(unquote(q["msg"]))
        if path in ("/set", "/import"):
            return 200, "ok", "text/plain"
        return 200, self.page(q.get("k", "")), "text/html"

    def page(self, k=""):
        return page.PAGE

    def say(self, text):
        """Scroll a message from the web page across the ticker once (only while the idle screen shows)."""
        text = "".join(ch for ch in text.upper() if ch in FONT)[:60].strip()
        if text:
            self.ticker += [("|", (90, 90, 90)), (text, (255, 120, 200)), ("|", (90, 90, 90))]
            self.ticker_width = board.marquee_width(self.ticker)

    def follow(self):
        """Make LEAGUES follow the teams in settings. A sport whose teams changed forgets its old games."""
        now = time.ticks_ms()
        for s in apply_teams():
            sport = SPORTS[s]["sport"]
            self.team_gen[s] += 1
            self.data.pop(s, None)
            self.anims = [a for a in self.anims if a.key[0] != sport]
            self.fails.pop(("poll", s), None)
            if self.due:
                self.due[("poll", s)] = now
            log("following", sport, ",".join(f["abbr"] for f in LEAGUES if f["sport"] == sport))
        keys = [(f["sport"], f["abbr"]) for f in LEAGUES]
        for k in list(self.upcoming):
            if k not in keys:
                del self.upcoming[k]
        for k in list(self.standings):
            if k not in keys:
                del self.standings[k]
        if self.due:  # a next-game lookup for each team followed now, none for the ones dropped
            for k in list(self.due):
                if k[0] in ("next", "stand") and k[1] not in keys:
                    del self.due[k]
                    self.fails.pop(k, None)
            for k in keys:
                self.due.setdefault(("next", k), now)
                if k[0] == "baseball":
                    self.due.setdefault(("stand", k), now + 15000)
        self.slide_drawn = None
        self.dirty = True

    # -- network jobs ----------------------------------------------------
    def schedule_jobs(self):
        now = time.ticks_ms()
        self.due = {("ntp", 0): time.ticks_add(now, NTP_REFRESH * 1000), ("wx", 0): now}
        for s in range(len(SPORTS)):
            self.due[("poll", s)] = now
            self.due[("all", s)] = time.ticks_add(now, 20000 * (s + 1))
            self.due[("news", s)] = time.ticks_add(now, 60000 + 25000 * s)
        for f in LEAGUES:
            self.due[("next", (f["sport"], f["abbr"]))] = now
            if f["sport"] == "baseball":
                self.due[("stand", (f["sport"], f["abbr"]))] = time.ticks_add(now, 15000)

    def run_job(self):
        """Run the most important job that is due (at most one per call)."""
        now = time.ticks_ms()
        ready = [k for k, t in self.due.items() if time.ticks_diff(now, t) >= 0]
        if not ready:
            return
        key = min(ready, key=lambda k: PRIORITY[k[0]])
        kind, i = key
        self.job = "%s%s" % (kind, i if isinstance(i, int) else ":".join(i))
        gen = self.team_gen[i] if kind == "poll" else 0
        try:
            value, wait = JOBS[kind](i)
            if kind == "poll" and gen != self.team_gen[i]:
                raise OSError("teams changed mid-download")  # drop it; the new teams are fetched next
            self.inbox.append((kind, i, True, value))
            self.fails.pop(key, None)
        except Exception as e:  # network hiccup: keep the old data, retry soon
            self.fails[key] = self.fails.get(key, 0) + 1
            log(kind, i, "failed:", repr(e))
            if isinstance(e, MemoryError):
                self.mem_errors += 1
            if isinstance(e, TypeError):  # a bug, not the network: say where
                try:
                    import io
                    import sys
                    tb = io.StringIO()
                    sys.print_exception(e, tb)
                    for ln in tb.getvalue().strip().split("\n")[-5:]:
                        log("  ", ln.strip())
                except Exception:
                    pass
            n = min(self.fails[key], 6)  # back off: 10 s, 20, 40, 80, 120 for scores; 1 min up to 15 for the rest
            wait = min(10 << (n - 1), 120) if kind == "poll" else min(60 << (n - 1), 900)
        if kind == "poll" and gen != self.team_gen[i]:
            wait = 0  # different teams now: fetch again straight away
            self.fails.pop(key, None)
        if kind in ("next", "stand") and not followed(*i):
            self.due.pop(key, None)  # unfollowed while it ran
            self.fails.pop(key, None)
        else:
            self.due[key] = time.ticks_add(time.ticks_ms(), wait * 1000)
        self.job = "gc"
        t = time.ticks_ms()
        gc.collect()
        dt = time.ticks_diff(time.ticks_ms(), t)
        if dt > 100:
            print("timing: gc took", dt, "ms")
        self.job = "-"

    def tick(self, waiting=True):
        """Called during network work: keep the watchdog fed and the display moving."""
        feed()
        if self.ota and time.ticks_diff(time.ticks_ms(), self.ota_next) >= 0:  # the settings page, even mid-download
            self.ota_next = time.ticks_add(time.ticks_ms(), 100)
            if self.ota.poll():
                self.slide_drawn = None
                self.dirty = True
        if time.ticks_diff(time.ticks_ms(), self.next_frame) >= 0:
            self.frame()
        elif waiting:
            time.sleep_ms(2)

    # -- main loop -------------------------------------------------------
    def run(self):
        message(("WIFI...", WHITE))
        pause = 5
        while not wifi_up():
            message(("NO WIFI", AMBER), ("RETRYING", GREY))
            for _ in range(pause * 2):
                feed()
                time.sleep_ms(500)
            pause = min(pause * 2, 60)  # 5, 10, 20, 40, 60 seconds between tries
        message(("CLOCK...", WHITE))
        self.clock_ok = sync_clock()
        self.follow()  # the teams chosen on the settings page
        self.load_cache()
        message(("LOADING", WHITE), ("SCORES", WHITE), (wlan.ifconfig()[0], GREY))
        for host in (espn.HOST, mlb.HOST, weather.HOST):  # look these up now, not mid-ticker
            try:
                feed()
                espn.resolve(host)
            except Exception as e:
                log("dns", host, "failed:", repr(e))
        espn.set_tick(self.tick)
        try:
            self.ota = ota.start(feed, lambda: message(("UPDATING", AMBER), ("DONT UNPLUG", GREY)), self.web)
        except Exception as e:
            log("ota off:", repr(e))
        log("ip", wlan.ifconfig()[0])
        self.schedule_jobs()
        self.next_frame = time.ticks_ms()
        self.worst_gap = 0
        self.loop()

    def frame(self):
        """Draw one frame for whatever the board is showing and schedule the next one."""
        now_ms = time.ticks_ms()
        late = time.ticks_diff(now_ms, self.next_frame)
        if late > self.worst_gap:
            self.worst_gap = late
        if late > 300:
            log("stall:", late, "ms late; net:", espn.where, "; job:", self.job)
        if self.anims:
            self.draw()
            delay = FRAME_MS
        elif self.views:
            close = any(v.get("close") for v in self.views)
            if self.dirty or time.ticks_diff(now_ms, self.last_draw) > (
                    CLOSE_MS if close else 1000 if self.ticking else 20000):
                self.refresh_views()
                self.draw()
                self.dirty = False
            delay = 200
        else:  # idle: clock/teams on top, ticker below, cameos now and then
            if not self.cameo:
                critters.release()
            self.slide = int(time.time()) // SLIDE_SECONDS
            if self.dirty or time.ticks_diff(now_ms, self.last_refresh) > 60000:
                self.refresh_views()
                self.dirty = False
            if self.ticker_stale and not self.ticker:
                self.build_ticker()
            self.offset += 1
            if self.offset >= self.ticker_width:
                self.build_ticker()
            if not self.cameo and self.clock_ok and (
                    self.mode == 2 or time.ticks_diff(now_ms, self.cameo_due) >= 0):
                self.start_cameo()
            self.draw()
            delay = FRAME_MS if self.cameo else IDLE_FRAME_MS[settings.cfg["speed"]]
        self.next_frame = time.ticks_add(time.ticks_ms(), delay)

    def loop(self):
        while True:
            now_ms = time.ticks_ms()
            feed()
            self.watch(now_ms)
            t = time.ticks_ms()
            self.drain()
            dt = time.ticks_diff(time.ticks_ms(), t)
            if dt > 150:
                print("timing: applying results took", dt, "ms")
            self.check_buttons()
            self.look()
            if self.ota and self.ota.poll():
                self.slide_drawn = None
                self.dirty = True
            if self.healthy_due and time.ticks_diff(now_ms, self.healthy_due) >= 0:
                ota.healthy()  # the new code has run for 90 s: no rollback needed
                self.healthy_due = None
            if time.ticks_diff(now_ms, self.cache_due) >= 0:
                self.save_cache()
            self.run_job()  # waits inside call tick(), which draws frames
            if time.ticks_diff(time.ticks_ms(), self.next_frame) >= 0:
                self.frame()
            time.sleep_ms(5)


def _wdt_off():
    return "nowdt" in os.listdir()


def main():
    global _wdt
    if not _wdt_off():
        _wdt = machine.WDT(timeout=WDT_MS)
    failures = 0
    while True:
        try:
            Scoreboard().run()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            failures += 1
            log("crash:", repr(e))
            try:  # where it happened, a few short lines for the /log page
                import io
                import sys
                tb = io.StringIO()
                sys.print_exception(e, tb)
                for ln in tb.getvalue().strip().split("\n")[-6:]:
                    log("  ", ln.strip())
            except Exception:
                pass
            settings.save_log()
            try:
                message(("ERROR", AMBER), ("RESTART", GREY))
            except Exception:
                pass
            for _ in range(10):
                feed()
                time.sleep_ms(500)
            gc.collect()
            if failures >= 3:
                machine.reset()


main()
