"""Smoke tests for app.py on a computer, with the board's hardware modules faked.

    python3 -m unittest test_app

Catches typos and crashes in the display loop, web page, cache and slides that the logic tests can't reach.
"""
import json
import os
import sys
import tempfile
import time
import types
import unittest

os.environ["TZ"] = "UTC"
time.tzset()

import gc

gc.mem_free = lambda: 100000  # MicroPython only

# MicroPython's time functions
_t0 = time.monotonic()
time.ticks_ms = lambda: int((time.monotonic() - _t0) * 1000)
time.ticks_add = lambda a, b: a + b
time.ticks_diff = lambda a, b: a - b
time.sleep_ms = lambda ms: None


class FakeG:
    def create_pen(self, r, g, b):
        return (r, g, b)

    def set_pen(self, p):
        pass

    def rectangle(self, *a):
        pass


class FakeI75:
    width, height = 64, 32

    def __init__(self, display=None):
        self.display = FakeG()
        self.updates = 0

    def update(self):
        self.updates += 1

    def switch_pressed(self, n):
        return False


def stub(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


class WLAN:
    def __init__(self, *a):
        self.up = True

    def isconnected(self):
        return self.up

    def active(self, *a):
        pass

    def ifconfig(self):
        return ("10.0.0.5",)

    def status(self, *a):
        return -50


stub("machine", WDT=lambda timeout=0: types.SimpleNamespace(feed=lambda: None), reset=lambda: None)
stub("network", WLAN=WLAN, STA_IF=0, hostname=lambda n: None)
stub("ntptime", settime=lambda: None)
stub("interstate75", Interstate75=FakeI75, DISPLAY_INTERSTATE75_64X32=0, SWITCH_A=0, SWITCH_B=1)
stub("secrets", WIFI_SSID="a", WIFI_PASSWORD="b", OTA_KEY="k")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(tempfile.mkdtemp())  # config.json, cache.json, log.txt land here, not in the project

import settings  # noqa: E402

# app.py ends with main(), which would run forever: load it without that line
src = open(os.path.join(HERE, "app.py")).read().replace("\nmain()\n", "\n")
app = types.ModuleType("app")
exec(compile(src, "app.py", "exec"), app.__dict__)

GAME = dict(sport="football", name="KC @ SEA", date="2026-10-31T20:00Z", away="KC", away_score=10, home="SEA",
            home_score=7, clock="5:21", period=3, state="pre", detail="5:21 - 3rd")
NOW = time.mktime((2026, 10, 31, 20, 0, 0, 0, 0, 0))


class AppTest(unittest.TestCase):
    def setUp(self):
        settings.cfg.update(settings.DEFAULTS)
        app.apply_teams()  # the original three teams
        self.sb = app.Scoreboard()
        self.sb.clock_ok = True
        self.sb.upcoming = {("baseball", "LAD"): {"date": "2026-11-01T02:10Z", "name": "SF @ LAD", "time_valid": True,
                                                  "record": "8-5", "streak": 3},
                            ("football", "SEA"): {"date": "2026-11-02T01:00Z", "name": "LAR @ SEA", "time_valid": True,
                                                  "record": None, "streak": 0}}

    def test_every_idle_slide_draws(self):
        for slide in range(len(app.LEAGUES) + 2):
            self.sb.slide_drawn = None
            self.sb.slide = slide
            self.sb.mode = 0
            self.sb.idle_screen()  # raises on a typo
        self.sb.slide = 0
        self.sb.draw()

    def test_frames_run(self):
        self.sb.build_ticker()
        for _ in range(50):
            self.sb.frame()
            self.sb.next_frame = 0

    def test_status_pixel(self):
        self.sb.fails[("poll", 0)] = 3
        self.sb.flush()
        app.wlan.up = False
        self.sb.net_check = 0
        self.sb.flush()
        app.wlan.up = True

    def test_web_page_and_settings(self):
        code, body, ctype = self.sb.web("GET", "/ui", {"k": "k", "bright": "25", "cameos": "3", "mode": "2"})
        self.assertEqual((code, ctype), (200, "text/html"))
        self.assertEqual(settings.cfg["bright"], 25)
        self.assertEqual(self.sb.mode, 2)
        self.assertIn("Scoreboard", body)
        self.assertEqual(app.brightness_for(3), 0.25)
        self.sb.web("GET", "/ui", {"k": "k", "bright": "abc", "lat": "999"})  # rejected, not a crash
        self.assertEqual(settings.cfg["bright"], 25)
        self.assertEqual(settings.cfg["lat"], settings.DEFAULTS["lat"])
        self.assertIsNone(self.sb.web("GET", "/nope", {"k": "k"}))
        self.assertEqual(self.sb.web("GET", "/log", {"k": "k"})[0], 200)

    def test_web_set_state_and_message(self):
        self.assertEqual(self.sb.web("GET", "/set", {"k": "k", "display": "0"}), (200, "ok", "text/plain"))
        self.assertEqual(settings.cfg["display"], 0)
        self.assertEqual(app.brightness_for(12), 0.0)
        code, body, ctype = self.sb.web("GET", "/state", {"k": "k"})
        self.assertEqual((code, ctype), (200, "application/json"))
        self.assertEqual(app.json.loads(body)["display"], 0)
        self.sb.web("GET", "/set", {"k": "k", "display": "1"})
        self.sb.ticker = [("A", (1, 1, 1))]
        self.sb.web("GET", "/set", {"k": "k", "msg": "dinner%20is+ready%21"})
        self.assertEqual(self.sb.ticker[-2][0], "DINNER IS READY!")

    def test_choose_teams(self):
        self.sb.upcoming[("hockey", "SEA")] = {"name": "X @ SEA"}
        self.sb.data[2] = [GAME]
        gen = self.sb.team_gen[2]
        code, body, _ = self.sb.web("GET", "/teams", {"k": "k", "sport": "hockey"})
        self.assertEqual(code, 200)
        self.assertIn(["UTA", "Utah Mammoth"], app.json.loads(body))
        self.sb.web("GET", "/set", {"k": "k", "team_hockey": "UTA", "team_baseball": "SEA"})
        self.assertEqual([l["abbr"] for l in app.LEAGUES], ["SEA", "SEA", "UTA", "GS", "SEA"])
        self.assertEqual((app.LEAGUES[2]["abbr"], app.LEAGUES[2]["nick"]), ("UTA", "MAMMOTH"))
        self.assertEqual((app.LEAGUES[0]["abbr"], app.LEAGUES[0]["mlb_team_id"]), ("SEA", 136))
        self.assertEqual(self.sb.team_gen[2], gen + 1)
        self.assertNotIn(("hockey", "SEA"), self.sb.upcoming)  # the dropped team's games are forgotten
        self.assertNotIn(2, self.sb.data)
        self.sb.web("GET", "/set", {"k": "k", "team_football": "NOPE"})  # not a team: ignored, nothing breaks
        self.assertEqual(app.LEAGUES[1]["abbr"], "SEA")
        settings.cfg["team_football"] = "ZZZ"  # a bad saved value goes back to the original team
        self.sb.follow()
        self.assertEqual(settings.cfg["team_football"], "SEA")
        for sport, abbr in (("hockey", "SEA"), ("baseball", "LAD")):
            self.sb.web("GET", "/set", {"k": "k", "team_" + sport: abbr})
        self.assertEqual([l["abbr"] for l in app.LEAGUES], ["LAD", "SEA", "SEA", "GS", "SEA"])
        self.assertEqual(app.LEAGUES[2]["label"], "KRK")

    def test_follow_several_teams_in_a_sport(self):
        self.sb.schedule_jobs()
        self.sb.web("GET", "/set", {"k": "k", "team_baseball": "LAD,SF,SEA", "team_football": "SEA,KC"})
        self.assertEqual([(l["sport"], l["abbr"]) for l in app.LEAGUES],
                         [("baseball", "LAD"), ("baseball", "SF"), ("baseball", "SEA"),
                          ("football", "SEA"), ("football", "KC"), ("hockey", "SEA"),
                          ("basketball", "GS"), ("soccer", "SEA")])
        self.assertEqual(settings.cfg["team_baseball"], "LAD,SF,SEA")
        nexts = sorted(k[1] for k in self.sb.due if k[0] == "next")  # one next-game lookup per team
        self.assertEqual(nexts, sorted((l["sport"], l["abbr"]) for l in app.LEAGUES))
        self.assertEqual(sum(1 for k in self.sb.due if k[0] == "poll"), 5)  # but one score poll per sport
        self.sb.web("GET", "/set", {"k": "k", "team_baseball": "LAD,SF,SEA,NYY"})
        self.assertEqual(settings.cfg["team_baseball"], "LAD,SF,SEA,NYY")
        self.sb.web("GET", "/set", {"k": "k", "team_baseball": "LAD,SF,SEA,NYY,BOS"})  # at most 4 per sport: refused
        self.assertEqual(settings.cfg["team_baseball"], "LAD,SF,SEA,NYY")
        self.sb.web("GET", "/set", {"k": "k", "team_baseball": "LAD"})  # dropping teams drops their jobs and data
        self.assertEqual(sorted(k[1][1] for k in self.sb.due if k[0] == "next" and k[1][0] == "baseball"), ["LAD"])
        self.assertNotIn(("baseball", "SF"), self.sb.upcoming)
        # every idle slide still draws with extra teams
        for slide in range(len(app.LEAGUES) + 2):
            self.sb.slide = slide
            self.sb.slide_drawn = None
            self.sb.draw()

    def test_poll_asks_for_every_followed_team(self):
        seen = {}
        app.mlb.fetch = lambda ids: seen.setdefault("mlb", list(ids)) and []
        app.espn.fetch = lambda sport, path, abbrs, early: seen.update({sport: (abbrs, early)}) or []
        app.wifi_up = lambda: True
        self.sb.web("GET", "/set", {"k": "k", "team_baseball": "LAD,SF", "team_football": "SEA,KC"})
        for i in range(3):
            app.job_poll(i)
        self.assertEqual(seen["mlb"], [119, 137])
        self.assertEqual(seen["football"], (("SEA", "KC"), False))  # two teams: no early exit
        self.assertEqual(seen["hockey"], (("SEA",), False))
        self.sb.web("GET", "/set", {"k": "k", "team_football": "SEA"})
        app.job_poll(1)
        self.assertEqual(seen["football"], (("SEA",), True))

    def test_game_between_two_followed_teams_shows_once(self):
        self.sb.web("GET", "/set", {"k": "k", "team_football": "SEA,KC"})
        live = dict(GAME, state="in")
        self.sb.data[1] = [live]
        self.sb.refresh_views()
        self.assertEqual(len(self.sb.views), 1)
        self.assertIn(self.sb.views[0]["ours"], ("away", "home"))  # one card, with a followed team on it
        self.sb.detect_changes(app.SPORTS[1], [dict(live, away_score=10)])
        self.sb.detect_changes(app.SPORTS[1], [dict(live, away_score=17)])  # KC scores 7: counts as ours
        self.assertTrue(self.sb.anims and self.sb.anims[-1].ours)
        self.assertEqual(self.sb.anims[-1].color, app.follow_entry("football", "KC")["color"])

    def test_next_job_for_unfollowed_team_is_dropped(self):
        app.wifi_up = lambda: True
        with self.assertRaises(OSError):
            app.job_next(("football", "KC"))  # nobody follows KC

    def test_team_cameos_only_for_followed_teams(self):
        for _ in range(200):
            c = app.critters.pick(6, 1, [("hockey", "UTA")])
            self.assertNotIn(type(c), app.critters.TEAMS)
        seen = {type(app.critters.pick(6, 1, [("baseball", "LAD")])) for _ in range(300)}
        self.assertIn(app.critters.DodgerBall, seen)
        self.assertNotIn(app.critters.HawkFly, seen)

    def test_cameo_rates(self):
        settings.cfg["cameos"] = 3
        self.sb.start_cameo()
        self.assertGreaterEqual(time.ticks_diff(self.sb.cameo_due, time.ticks_ms()), 3500 * 1000)

    def test_cache_round_trip(self):
        live = dict(GAME, state="in")
        self.sb.all_games = {1: [GAME, live]}
        self.sb.weather = ("rain", "54F")
        self.sb.save_cache()
        fresh = app.Scoreboard()
        fresh.clock_ok = True
        fresh.load_cache()
        self.assertEqual(len(fresh.all_games[1]), 1)  # live games are not trusted from a cache
        self.assertEqual(fresh.upcoming[("baseball", "LAD")]["record"], "8-5")
        self.assertEqual(fresh.weather, ("rain", "54F"))

    def test_old_cache_ignored(self):
        settings.save_cache({"t": int(time.time()) - 7 * 3600, "up": {"0": {"date": "x"}}, "all": {}})
        fresh = app.Scoreboard()
        fresh.clock_ok = True
        fresh.load_cache()
        self.assertEqual(fresh.upcoming, {})

    def test_shutout_banner(self):
        self.sb.detect_changes(app.LEAGUES[1], [dict(GAME, state="in", home_score=7, away_score=0)])
        self.sb.detect_changes(app.LEAGUES[1], [dict(GAME, state="post", home_score=7, away_score=0)])
        self.assertEqual(self.sb.anims[-1].text, "SHUTOUT!")

    def test_job_failures_counted(self):
        def boom(i):
            raise OSError("down")
        app.JOBS["wx"] = boom
        self.sb.due = {("wx", 0): 0}
        for _ in range(3):
            self.sb.due[("wx", 0)] = 0
            self.sb.run_job()
        self.assertEqual(self.sb.fails[("wx", 0)], 3)
        self.assertIn("wx", settings.read_log())

    def test_sun_brightness_and_quiet_hours(self):
        noon = time.mktime((2026, 10, 31, 20, 0, 0, 0, 0, 0))  # 1 PM Pacific
        night = time.mktime((2026, 10, 31, 10, 0, 0, 0, 0, 0))  # 3 AM Pacific
        self.assertEqual(app.brightness_for(13, noon), 1.0)
        self.assertEqual(app.brightness_for(3, night), 0.25)
        rise, sset = app.sun_today(noon)
        self.assertEqual(app.brightness_for(10, sset - 1800), 0.6)  # the hour before sunset
        settings.cfg["sunbright"] = 0
        self.assertEqual(app.brightness_for(13, noon), 1.0)  # clock hours
        settings.cfg["qs"], settings.cfg["qe"] = 23, 6
        self.assertEqual(app.brightness_for(3, night), 0.0)
        self.assertEqual(app.brightness_for(13, noon), 1.0)
        self.assertEqual(app.brightness_for(3), 0.25)  # no clock yet: quiet hours cannot apply

    def test_export_and_import(self):
        settings.cfg["bright"] = 50
        code, body, ctype = self.sb.web("GET", "/export", {"k": "k"})
        self.assertEqual(app.json.loads(body)["bright"], 50)
        settings.cfg["bright"] = 0
        self.assertEqual(self.sb.web("GET", "/import", {"k": "k", "json": "%7B%22bright%22%3A25%2C%22qs%22%3A22%7D"})[0], 200)
        self.assertEqual((settings.cfg["bright"], settings.cfg["qs"]), (25, 22))
        self.assertEqual(self.sb.web("GET", "/import", {"k": "k", "json": "oops"})[0], 400)

    def test_failures_back_off(self):
        def boom(i):
            raise OSError("down")
        app.JOBS["poll"] = boom
        waits = []
        for _ in range(8):
            self.sb.due = {("poll", 0): 0}
            self.sb.run_job()
            waits.append(self.sb.due[("poll", 0)] - time.ticks_ms())
        self.assertLess(waits[0], waits[2])
        self.assertLessEqual(max(waits), 120500)

    def test_stale_score_marks_the_pixel(self):
        live = dict(GAME, state="in")
        self.sb.shown = [(app.LEAGUES[1], live)]
        now = time.ticks_ms()
        self.sb.fresh = {1: now}
        self.assertFalse(self.sb.data_stale(now))
        self.assertTrue(self.sb.data_stale(now + app.STALE_DATA_MS + 1))

    def test_close_game_pulses(self):
        close = dict(GAME, state="in", period=4, home_score=17, away_score=14)
        self.sb.views = [app.make_view(app.LEAGUES[1], close, NOW)]
        self.assertTrue(self.sb.views[0]["close"])
        for _ in range(3):
            self.sb.pulse()

    def test_daily_restart(self):
        resets = []
        app.machine.reset = lambda: resets.append(1)
        self.sb.boot_epoch = time.time() - 7 * 3600
        self.sb.watch(time.ticks_ms())
        self.assertEqual(resets, [] if app.local_now(time.time())[3] != app.RESTART_HOUR else [1])
        real = app.local_now
        app.local_now = lambda t: (2026, 10, 31, app.RESTART_HOUR, 5, 0, 5, 0, 0)
        try:
            self.sb.watch(time.ticks_ms())
            self.assertEqual(len(resets), 1)
            self.sb.views = [object()]  # a game is on: never restart
            self.sb.watch(time.ticks_ms())
            self.assertEqual(len(resets), 1)
        finally:
            app.local_now = real

    def test_reminders(self):
        import tempfile
        old = settings.REMINDERS
        settings.REMINDERS = os.path.join(tempfile.mkdtemp(), "r.json")
        del settings.reminders[:]
        try:
            self.assertEqual(self.sb.web("GET", "/rem_add", {"text": "take%20out%20trash", "date": "2026-11-07", "time": "18:00", "rep": "0"})[0], 200)
            self.assertEqual(self.sb.web("GET", "/rem_add", {"text": "", "date": "2026-11-07"})[0], 400)
            self.assertEqual(self.sb.web("GET", "/rem_add", {"text": "x", "date": "2026-13-07"})[0], 400)
            settings.add_reminder("daily thing", "2026-11-01", "", 1)
            settings.add_reminder("weekly", "2026-11-01", "", 2)  # a Sunday
            sat = (2026, 11, 7, 18, 30, 0, 5, 0, 0)
            self.assertEqual([t for t, _ in settings.active_reminders(sat)], ["TAKE OUT TRASH", "DAILY THING"])
            self.assertEqual([t for t, _ in settings.active_reminders((2026, 11, 7, 22, 0, 0, 5, 0, 0))], ["DAILY THING"])
            self.assertEqual(len(settings.reminders), 3)
            self.assertEqual([t for t, _ in settings.active_reminders((2026, 11, 8, 9, 0, 0, 6, 0, 0))], ["DAILY THING", "WEEKLY"])
            self.assertEqual(len(settings.reminders), 2)  # the one-off is over: dropped
            real = app.local_now
            app.local_now = lambda t: sat
            try:
                settings.add_reminder("a long reminder that wraps over lines", "2026-11-07", "", 0)
                for slide in range(len(app.LEAGUES) + 5):
                    self.sb.slide_drawn = None
                    self.sb.slide = slide
                    self.sb.idle_screen()
            finally:
                app.local_now = real
            self.assertEqual(self.sb.web("GET", "/rem_del", {"i": "0"})[0], 200)
            self.assertEqual(self.sb.web("GET", "/rem_del", {"i": "99"})[0], 400)
            settings.load_reminders()
            self.assertEqual(len(settings.reminders), len(json.loads(self.sb.web("GET", "/reminders", {})[1])))
        finally:
            settings.REMINDERS = old
            del settings.reminders[:]

    def test_countdown_standings_and_format(self):
        import tempfile
        old = settings.REMINDERS
        settings.REMINDERS = os.path.join(tempfile.mkdtemp(), "r.json")
        del settings.reminders[:]
        try:
            settings.add_reminder("opening day", "2026-11-12", "", 3)
            self.assertEqual(settings.active_reminders((2026, 11, 10, 9, 0, 0, 1, 0, 0)), [("OPENING DAY", 2)])
            self.assertEqual(settings.active_reminders((2026, 11, 12, 9, 0, 0, 3, 0, 0)), [("OPENING DAY", 0)])
            settings.add_reminder("far", "2027-06-01", "", 3)
            self.assertEqual(len(settings.active_reminders((2026, 11, 12, 9, 0, 0, 3, 0, 0))), 1)  # too far ahead
            self.assertEqual(len(settings.active_reminders((2026, 11, 13, 9, 0, 0, 4, 0, 0))), 0)   # the first one is over
            self.assertEqual(settings._days(2026, 3, 1) - settings._days(2026, 2, 1), 28)
            self.sb.standings[("baseball", "LAD")] = (203, [("LAD", 90, 72), ("SD", 85, 77), ("SF", 80, 82), ("AZ", 70, 92), ("COL", 50, 112)])
            pages = self.sb.extra_slides((2026, 11, 10, 9, 0, 0, 1, 0, 0))
            self.assertEqual(len(pages), 2)  # rows 1-3, then rows 4-5 under the division name (the far countdown is not shown yet)
        finally:
            settings.REMINDERS = old
            del settings.reminders[:]

    def test_24_hour_and_speed(self):
        self.sb.web("GET", "/set", {"h24": "1", "speed": "3"})
        self.assertTrue(app.scores.H24)
        self.assertEqual(app.scores.hhmm_text(18, 5), "18:05")
        self.sb.web("GET", "/set", {"h24": "0"})
        self.assertFalse(app.scores.H24)
        self.assertEqual(app.scores.hhmm_text(18, 5), "6:05P")
        for slide in range(len(app.LEAGUES) + 4):
            self.sb.slide_drawn = None
            self.sb.slide = slide
            self.sb.idle_screen()
        settings.cfg.update(settings.DEFAULTS)

    def test_slide_wipe(self):
        self.sb.mode = 0
        self.sb.slide = 0
        self.sb.idle_screen()
        self.assertEqual(self.sb.wipe, 0)
        self.sb.slide = 1
        for left in range(app.WIPE_FRAMES - 1, -1, -1):
            self.sb.idle_screen()
            self.assertEqual(self.sb.wipe, left)
        self.sb.idle_screen()
        self.assertEqual(self.sb.wipe, 0)
        self.assertIsNotNone(self.sb.slide_drawn)  # settled: drawn once, no more redraws

    def test_restart_when_memory_fragmented(self):
        resets = []
        real = app.machine.reset
        app.machine.reset = lambda: resets.append(1)
        try:
            self.sb.boot_epoch = time.time() - 3600
            self.sb.views = []
            self.sb.anims = []
            self.sb.cameo = None
            self.sb.mem_errors = app.MEM_ERRORS_RESTART - 1
            self.sb.watch(time.ticks_ms())
            self.assertEqual(resets, [])
            self.sb.mem_errors = app.MEM_ERRORS_RESTART
            self.sb.views = [object()]  # a game is on: not now
            self.sb.watch(time.ticks_ms())
            self.assertEqual(resets, [])
            self.sb.views = []
            self.sb.watch(time.ticks_ms())
            self.assertEqual(len(resets), 1)
        finally:
            app.machine.reset = real

    def test_team_page_stream(self):
        import espn
        page = (b'{"team":{"record":{"items":[{"summary":"9-6","stats":[{"name":"streak","value":-1.0}]}]},'
                b'"nextEvent":[{"competitions":[{"date":"2026-11-12T17:00Z","media":{"shortName":"TV"}}],'
                b'"date":"2026-11-12T17:00Z","name":"Carolina at Seattle","shortName":"CAR vs. SEA","timeValid":true}]}}')
        for size in (7, 50, 1024):  # however the network cuts it up
            p = espn._TeamPage()
            for i in range(0, len(page), size):
                p.add(page[i:i + size])
            self.assertEqual(p.result(), {"date": "2026-11-12T17:00Z", "name": "CAR VS SEA", "time_valid": True,
                                          "record": "9-6", "streak": -1}, size)


if __name__ == "__main__":
    unittest.main()


class TestImprovements(unittest.TestCase):
    """Spoiler delay, timer and stopwatch, ticker filter, magic number and wild card slides."""

    def setUp(self):
        self.sb = app.Scoreboard.__new__(app.Scoreboard)
        self.sb.__init__()

    def test_clock_text(self):
        self.assertEqual(app.clock_text(65), "1:05")
        self.assertEqual(app.clock_text(3725), "1:02:05")

    def test_timer_counts_down_then_rings(self):
        self.sb.set_timer({"timer": "90"})
        lines = self.sb.timer_lines()
        self.assertEqual(lines[0][0], "TIMER")
        self.assertIn(lines[1][0], ("1:30", "1:29"))
        self.sb.timer_end = app.time.ticks_add(app.time.ticks_ms(), -1000)
        self.assertEqual(self.sb.timer_lines()[0][0], "TIME'S UP!")
        self.sb.timer_over = app.time.ticks_add(app.time.ticks_ms(), -61000)
        self.assertIsNone(self.sb.timer_lines())
        self.sb.set_timer({"timer": "30"})
        self.sb.set_timer({"timer": "0"})
        self.assertIsNone(self.sb.timer_lines())

    def test_stopwatch_pause_and_clear(self):
        self.sb.set_timer({"stopwatch": "1"})
        self.assertEqual(self.sb.timer_lines()[0][0], "STOPWATCH")
        self.sb.stopwatch = [app.time.ticks_add(app.time.ticks_ms(), -5000), 0]
        self.sb.set_timer({"stopwatch": "0"})
        lines = self.sb.timer_lines()
        self.assertEqual(lines[0][0], "PAUSED")
        self.assertEqual(lines[1][0], "0:05")
        self.sb.set_timer({"stopwatch": "clear"})
        self.assertIsNone(self.sb.timer_lines())

    def test_spoiler_delay_holds_scores_back(self):
        old = app.settings.cfg["delay"]
        try:
            app.settings.cfg["delay"] = 30
            self.sb.data[0] = []
            self.sb.inbox.append(("poll", 0, True, ["new"]))
            self.sb.apply = lambda *a: self.sb.applied.append(a)
            self.sb.applied = []
            self.sb.drain()
            self.assertEqual(self.sb.applied, [])        # held
            self.sb.held[("poll", 0)][0] = app.time.ticks_add(app.time.ticks_ms(), -1)
            self.sb.drain()
            self.assertEqual(self.sb.applied, [("poll", 0, True, ["new"])])
            app.settings.cfg["delay"] = 30               # no data yet for a sport: shown at once
            self.sb.inbox.append(("poll", 2, True, ["first"]))
            self.sb.drain()
            self.assertEqual(self.sb.applied[-1], ("poll", 2, True, ["first"]))
        finally:
            app.settings.cfg["delay"] = old

    def test_magic_number_and_wild_card_slides(self):
        old = list(app.LEAGUES)
        try:
            lad = [l for l in app.LEAGUES if l["abbr"] == "LAD"][0]
            self.sb.standings[("baseball", "LAD")] = (203, [("LAD", 90, 72), ("SD", 85, 77)], {"LAD": ("7", "", "-")})
            texts = [[t if isinstance(t, str) else "" for t, _ in page] for page in self.sb.extra_slides((2026, 9, 1, 9, 0, 0, 1, 0, 0))]
            self.assertIn(["LAD", "MAGIC NUMBER", "7"], texts)
            self.sb.standings[("baseball", "LAD")] = (203, [("SD", 90, 72), ("LAD", 85, 77)], {"LAD": ("", "2", "+1.5")})
            texts = [[t for t, _ in page if isinstance(t, str)] for page in self.sb.extra_slides((2026, 9, 1, 9, 0, 0, 1, 0, 0))]
            self.assertIn(["LAD", "WILD CARD 2", "1.5 AHEAD"], texts)
        finally:
            app.LEAGUES[:] = old
