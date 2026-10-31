"""Smoke tests for app.py on a computer, with the board's hardware modules faked.

    python3 -m unittest test_app

Catches typos and crashes in the display loop, web page, cache and slides that the logic tests can't reach.
"""
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
        self.sb = app.Scoreboard()
        self.sb.clock_ok = True
        self.sb.upcoming = {0: {"date": "2026-11-01T02:10Z", "name": "SF @ LAD", "time_valid": True,
                                "record": "8-5", "streak": 3},
                            1: {"date": "2026-11-02T01:00Z", "name": "LAR @ SEA", "time_valid": True,
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
        self.assertEqual(fresh.upcoming[0]["record"], "8-5")
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


if __name__ == "__main__":
    unittest.main()
