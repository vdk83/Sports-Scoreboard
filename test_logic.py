"""Tests for the pure game logic. Run on a computer:  python3 -m unittest test_logic

The board's clock counts from 2000, a computer's from 1970, but scores.py only uses
mktime/gmtime in matching pairs, so with TZ=UTC the results agree.
"""
import os
import time
import unittest

os.environ["TZ"] = "UTC"
time.tzset()

import scores  # noqa: E402
from scores import LEAGUES, banner, importance, local_time_str, make_view, marquee_parts, status_text, tag, visible  # noqa: E402

LAD, SEA_NFL, SEA_NHL = LEAGUES


def game(**kw):
    g = dict(sport="football", name="KC @ SEA", date="2026-10-25T20:00Z", away="KC", away_score=10, home="SEA",
             home_score=7, clock="5:21", period=3, state="in", detail="5:21 - 3rd")
    g.update(kw)
    return g


def epoch(y, mo, d, h=0, mi=0):
    return scores.iso_to_epoch("%04d-%02d-%02dT%02d:%02dZ" % (y, mo, d, h, mi))


class Time(unittest.TestCase):
    def test_dst_boundaries(self):
        self.assertEqual(scores.utc_offset(epoch(2026, 3, 8, 9, 59)), -8)
        self.assertEqual(scores.utc_offset(epoch(2026, 3, 8, 10, 0)), -7)
        self.assertEqual(scores.utc_offset(epoch(2026, 11, 1, 8, 59)), -7)
        self.assertEqual(scores.utc_offset(epoch(2026, 11, 1, 9, 0)), -8)

    def test_local_time_str(self):
        now = epoch(2026, 10, 25, 12)
        self.assertEqual(local_time_str("2026-10-25T20:10Z", now), "1:10P")
        self.assertTrue(local_time_str("2026-10-26T20:10Z", now).startswith("MON"))


class Status(unittest.TestCase):
    now = epoch(2026, 10, 25, 20)

    def test_football(self):
        self.assertEqual(status_text(game(), self.now), "Q3 5:21")
        self.assertEqual(status_text(game(period=5), self.now), "OT 5:21")
        self.assertEqual(status_text(game(detail="Halftime"), self.now), "HALFTIME")
        self.assertEqual(status_text(game(state="post", detail="Final"), self.now), "FINAL")

    def test_hockey(self):
        g = game(sport="hockey", period=4)
        self.assertEqual(status_text(g, self.now), "OT 5:21")
        self.assertEqual(status_text(dict(g, period=2, detail="End of 2nd"), self.now), "END P2")

    def test_baseball(self):
        g = game(sport="baseball", detail="Top 7th")
        self.assertEqual(status_text(g, self.now), "^7")
        self.assertEqual(status_text(dict(g, detail="Bottom 8th"), self.now), "v8")
        self.assertEqual(status_text(dict(g, detail="Middle 3rd"), self.now), "MID 3")


class Banners(unittest.TestCase):
    def test_football(self):
        g = game()
        self.assertEqual(banner(SEA_NFL, g, "home", 7), ("TOUCHDOWN!", True))
        self.assertEqual(banner(SEA_NFL, g, "home", 3), ("FIELD GOAL!", True))
        self.assertEqual(banner(SEA_NFL, g, "away", 7), ("KC +7", False))

    def test_hockey_baseball(self):
        self.assertEqual(banner(SEA_NHL, game(sport="hockey"), "home", 1), ("GOAL!", True))
        self.assertEqual(banner(LAD, game(sport="baseball", home="LAD"), "home", 4), ("4 RUNS!", True))


class Importance(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(importance(game()), 0)
        self.assertEqual(importance(game(playoff=True, note="NLCS")), 1)
        self.assertEqual(importance(game(playoff=True, note="World Series Game 3")), 2)
        self.assertEqual(tag(game(playoff=True, note="Super Bowl LXI")), "SB")
        self.assertEqual(tag(game(playoff=True, note="Wild Card")), "PO")


class Visible(unittest.TestCase):
    now = epoch(2026, 10, 25, 22)

    def test_pre_games_stay_off_the_board(self):
        out = visible([(SEA_NFL, [game(state="pre")])], self.now, True)
        self.assertEqual(out, [])

    def test_old_final_drops_off(self):
        old = game(state="post", date="2026-10-24T20:00Z")
        self.assertEqual(visible([(SEA_NFL, [old])], self.now, True), [])
        self.assertEqual(len(visible([(SEA_NFL, [old])], self.now, False)), 1)

    def test_live_first_and_max_four(self):
        games = [game(name="G%d" % i, state="post", date="2026-10-25T%02d:00Z" % (10 + i)) for i in range(5)]
        live = game(name="LIVE")
        out = visible([(SEA_NFL, games + [live])], self.now, True)
        self.assertEqual(len(out), 4)
        self.assertEqual(out[0][1]["name"], "LIVE")


class View(unittest.TestCase):
    def test_our_team_label(self):
        v = make_view(SEA_NHL, game(sport="hockey"), epoch(2026, 10, 25, 20))
        self.assertEqual(v["home"], "KRK")
        self.assertEqual(v["ours"], "home")

    def test_pre_hides_scores(self):
        v = make_view(SEA_NFL, game(state="pre"), epoch(2026, 10, 25, 12))
        self.assertIsNone(v["home_score"])


class Marquee(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(marquee_parts([(SEA_NFL, [])], time.time(), True), [("NO SCORES TODAY", scores.GREY)])

    def test_has_scores(self):
        now = epoch(2026, 10, 25, 22)
        text = " ".join(p[0] for p in marquee_parts([(SEA_NFL, [game()])], now, True))
        self.assertIn("NFL", text)
        self.assertIn("KC", text)


if __name__ == "__main__":
    unittest.main()
