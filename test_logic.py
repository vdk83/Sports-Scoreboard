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
import settings  # noqa: E402
import sun  # noqa: E402
from scores import LEAGUES, banner, importance, local_time_str, make_view, marquee_parts, status_text, tag, visible  # noqa: E402

LAD, SEA_NFL, SEA_NHL = LEAGUES[:3]  # the first three; basketball and soccer follow after them


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

    def test_pre_games_join_an_hour_before_the_start(self):
        self.assertEqual(visible([(SEA_NFL, [game(state="pre", date="2026-10-26T01:00Z")])], self.now, True), [])  # 3h away
        out = visible([(SEA_NFL, [game(state="pre", date="2026-10-25T22:50Z")])], self.now, True)  # 50 min away
        self.assertEqual(len(out), 1)
        self.assertEqual(visible([(SEA_NFL, [game(state="pre", date="2026-10-25T22:50Z")])], self.now, False), [])  # no clock

    def test_final_stays_an_hour_after_the_end(self):
        g = game(state="post", date="2026-10-25T17:00Z")  # a football game: ends about 20:15Z by the usual length
        self.assertEqual(visible([(SEA_NFL, [g])], self.now, True), [])  # 22:00Z is 1h45 after the guessed end
        ended = {scores.game_key("football", g): self.now - 1800}  # we saw it end half an hour ago
        self.assertEqual(len(visible([(SEA_NFL, [g])], self.now, True, (), ended)), 1)
        ended = {scores.game_key("football", g): self.now - 3700}
        self.assertEqual(visible([(SEA_NFL, [g])], self.now, True, (), ended), [])

    def test_old_final_drops_off(self):
        old = game(state="post", date="2026-10-24T20:00Z")
        self.assertEqual(visible([(SEA_NFL, [old])], self.now, True), [])
        self.assertEqual(len(visible([(SEA_NFL, [old])], self.now, False)), 1)

    def test_live_first_and_max_four(self):
        games = [game(name="G%d" % i, state="post", date="2026-10-25T%02d:00Z" % (18 + i)) for i in range(5)]
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


class Rivals(unittest.TestCase):
    def test_rival_tag_and_colour(self):
        g = game(sport="baseball", name="SF @ LAD", away="SF", home="LAD")
        self.assertEqual(make_view(LAD, g, epoch(2026, 10, 25, 20))["tag"], "RIV")
        self.assertIsNone(make_view(LAD, dict(g, away="COL"), epoch(2026, 10, 25, 20))["tag"])
        nx = {"date": "2026-11-01T02:10Z", "name": "SF @ LAD", "time_valid": True}
        self.assertEqual(scores.next_game_lines(LAD, nx, epoch(2026, 10, 31, 12))[0], ("VS SF", "rival"))

    def test_playoff_tag_wins_over_rival(self):
        g = game(sport="baseball", away="SF", home="LAD", playoff=True, note="World Series")
        self.assertEqual(make_view(LAD, g, epoch(2026, 10, 25, 20))["tag"], "WS")


class Record(unittest.TestCase):
    def test_text(self):
        self.assertEqual(scores.record_text({"record": "8-5-1", "streak": -2}), "8-5-1 L2")
        self.assertEqual(scores.record_text({"record": "8-5", "streak": 3}), "8-5 W3")
        self.assertEqual(scores.record_text({"record": "8-5", "streak": 0}), "8-5")
        self.assertEqual(scores.record_text({"record": None, "streak": 3}), "")
        self.assertEqual(scores.record_text(None), "")

    def test_shutout_wording(self):
        self.assertEqual(scores.result_text(True, 3, 0), "SHUTOUT!")
        self.assertEqual(scores.result_text(True, 3, 1), "WIN!")
        self.assertEqual(scores.result_text(False, 0, 3), "LOSS")


class Sun(unittest.TestCase):
    def test_santa_cruz_solstice(self):
        r, s = sun.times(37.03, -122.12, 2026, 12, 21)
        self.assertTrue(7.0 <= (r - 8) % 24 <= 7.4, r)    # about 7:10 PST
        self.assertTrue(16.8 <= (s - 8) % 24 <= 17.2, s)  # about 4:55 PST

    def test_polar_night(self):
        self.assertEqual(sun.times(80, 0, 2026, 12, 21), (None, None))

    def test_next_sun(self):
        name, at, mins = scores.next_sun(epoch(2026, 10, 31, 20))  # 1 pm Pacific
        self.assertEqual(name, "SUNSET")
        self.assertTrue(at.endswith("P"))
        self.assertTrue(240 < mins < 400)


class Settings(unittest.TestCase):
    def setUp(self):
        settings.cfg.update(settings.DEFAULTS)

    def test_validation(self):
        self.assertTrue(settings.set_value("bright", "25"))
        self.assertEqual(settings.cfg["bright"], 25)
        for key, bad in (("bright", "101"), ("mode", "7"), ("lat", "91"), ("lat", "north"), ("nope", "1")):
            self.assertFalse(settings.set_value(key, bad), (key, bad))
        self.assertEqual(settings.cfg["bright"], 25)
        self.assertTrue(settings.set_value("lat", "-33.9"))
        self.assertEqual(settings.cfg["lat"], -33.9)

    def test_log_is_bounded(self):
        for i in range(100):
            settings.log("line", i)
        self.assertLessEqual(len(settings._lines), settings.LOG_LINES)
        self.assertTrue(settings._lines[-1].endswith("line 99"))


class QuietAndClose(unittest.TestCase):
    def setUp(self):
        settings.cfg.update(settings.DEFAULTS)

    def test_quiet_hours_wrap_midnight(self):
        settings.cfg["qs"], settings.cfg["qe"] = 22, 6
        self.assertTrue(settings.quiet_now(23))
        self.assertTrue(settings.quiet_now(5))
        self.assertFalse(settings.quiet_now(6))
        self.assertFalse(settings.quiet_now(12))
        settings.cfg["qs"] = settings.cfg["qe"] = 3
        self.assertFalse(settings.quiet_now(3))

    def test_import_ignores_bad_values(self):
        self.assertEqual(settings.import_json('{"bright": 40, "lat": 999, "nope": 1}'), 1)
        self.assertEqual(settings.cfg["bright"], 40)
        self.assertEqual(settings.import_json("[1]"), 0)

    def test_sun_today_is_ordered(self):
        rise, sset = scores.sun_today(epoch(2026, 10, 31, 20))
        self.assertLess(rise, sset)
        self.assertEqual(scores.local_now(rise)[2], 31)

    def test_is_close(self):
        self.assertTrue(scores.is_close(game(period=4, home_score=20, away_score=14)))
        self.assertFalse(scores.is_close(game(period=2, home_score=20, away_score=14)))
        self.assertFalse(scores.is_close(game(period=4, home_score=30, away_score=14)))
        self.assertTrue(scores.is_close(game(sport="hockey", period=3, home_score=2, away_score=3)))
        self.assertTrue(scores.is_close(game(sport="baseball", period=9, home_score=2, away_score=2)))
        self.assertFalse(scores.is_close(game(sport="baseball", period=7, home_score=2, away_score=2)))
        self.assertFalse(scores.is_close(game(state="post", period=4)))

    def test_live_hockey_and_football_views(self):
        hk = make_view(LEAGUES[2], game(sport="hockey", period=2, clock="12:03", sog=(14, 21), pp="home", pp_on=True), 0)
        self.assertEqual(hk["hockey"], {"sog": (14, 21), "pp": "home", "pp_on": True, "goalies": {}})
        self.assertEqual(scores.short_status(game(sport="hockey", period=2, clock="12:03", pp_on=True), 0), "P2 PP")
        self.assertNotIn("hockey", make_view(LEAGUES[2], game(sport="hockey", period=2), 0))  # no extras fetched
        fb = make_view(LEAGUES[1], game(sport="football", period=3, clock="5:21"), 0)
        self.assertEqual((fb["quarter"], fb["status"]), (3, "Q3 5:21"))
        self.assertNotIn("quarter", make_view(LEAGUES[1], game(sport="football", period=5, clock="5:21"), 0))  # overtime

    def test_basketball_and_soccer(self):
        nba = dict(sport="basketball", state="in", detail="x", period=3, clock="5:21", away="LAL", home="GS", away_score=90, home_score=88)
        self.assertEqual(status_text(nba, 0), "Q3 5:21")
        self.assertEqual(status_text(dict(nba, period=5), 0), "OT 5:21")
        self.assertEqual(status_text(dict(nba, period=6), 0), "2OT 5:21")
        self.assertTrue(scores.is_close(dict(nba, period=4)))
        mls = dict(sport="soccer", state="in", period=2, clock="67'", detail="67'", away="POR", home="SEA", away_score=1, home_score=1)
        self.assertEqual(status_text(mls, 0), "67'")
        self.assertEqual(status_text(dict(mls, detail="HT", clock="45'+2'"), 0), "HALFTIME")
        self.assertTrue(scores.is_close(mls))
        self.assertEqual(scores.banner(scores.SPORTS[4], mls, "home", 1)[0][:4], "GOAL")

    def test_names_for_the_panel(self):
        import espn
        self.assertEqual(espn.last_name("Julio Rodr\u00edguez Jr."), "RODRIGUEZ")
        self.assertEqual(espn.last_name("Shohei Ohtani"), "OHTANI")
        self.assertEqual(espn.last_name("T. Lawrence"), "LAWRENCE")
        self.assertEqual(espn.last_name("Ronald Acu\\u00f1a Jr."), "ACUNA")  # escaped in the feed

    def test_player_lines_reach_the_views(self):
        bb = dict(sport="baseball", state="in", detail="Top 7th", bases=(True, False, False), outs=1, count="1-2",
                  abs=None, pitcher="KERSHAW", batter="OHTANI", period=7, clock="", away="SF", home="LAD",
                  away_score=1, home_score=2, date="2026-10-25T20:00Z", name="SF @ LAD")
        self.assertEqual((make_view(LAD, bb, 0)["live"]["pitcher"], make_view(LAD, bb, 0)["live"]["batter"]),
                         ("KERSHAW", "OHTANI"))
        fb = make_view(LEAGUES[1], game(sport="football", period=3, qb=("LAWRENCE", 242, "away")), 0)
        self.assertEqual(fb["qb"], ("LAWRENCE", 242, "away"))
        self.assertNotIn("qb", make_view(LEAGUES[1], game(sport="football", period=3), 0))

    def test_goalie_scan_any_chunk_size(self):
        import nhl
        def goalie(last):
            return (b'{"athlete":{"id":"1","lastName":"' + last + b'","displayName":"x","position":{"abbreviation":"G"}},'
                    b'"stats":["1"]}')
        stream = (b'{"boxscore":{"teams":[{"team":{"abbreviation":"MTL"},"statistics":[{"name":"goals","abbreviation":"G"}]}],'
                  b'"players":[{"team":{"id":"10","abbreviation":"MTL"},"statistics":[{"name":"forwards","athletes":[]},'
                  b'{"name":"goalies","athletes":[' + goalie(b"Fowler") + b']}]},'
                  b'{"team":{"id":"21","abbreviation":"TOR"},"statistics":[{"name":"goalies","athletes":['
                  + goalie(b"Woll") + b',' + goalie(b"Bobrovsky") + b']}]}]}' + b" " * 3000)
        for size in (50, 333, 1024, 5000):
            scan = nhl.GoalieScan()
            for i in range(0, len(stream), size):
                scan.add(stream[i:i + size])
            self.assertEqual(scan.names, {"MTL": "FOWLER", "TOR": "BOBROVSKY"}, size)  # the newest listed goalie wins

    def test_nhl_summary_and_situation(self):
        import nhl
        head = (b'{"boxscore":{"teams":[{"team":{"id":"10","abbreviation":"MTL","name":"x"},"statistics":['
                b'{"name":"shotsTotal","abbreviation":"S","displayValue":"13"},'
                b'{"name":"powerPlayOpportunities","abbreviation":"PPO","displayValue":"1"}]},'
                b'{"team":{"id":"21","abbreviation":"TOR"},"statistics":['
                b'{"name":"shotsTotal","abbreviation":"S","displayValue":"16"},'
                b'{"name":"powerPlayOpportunities","abbreviation":"PPO","displayValue":"2"}]}]}')
        self.assertEqual(nhl.parse_summary(head), [("MTL", 13, 1), ("TOR", 16, 2)])
        self.assertTrue(nhl.power_play_on(b'{"powerPlay":true,"emptyNet":false}'))
        self.assertFalse(nhl.power_play_on(b'{"powerPlay":false,"emptyNet":false}'))


if __name__ == "__main__":
    unittest.main()


class TestNews(unittest.TestCase):
    def test_headlines_any_chunk_size(self):
        import news
        j = (b'{"articles":[{"headline":"Kraken\\u2019s Tolvanen scores twice, beats \\"Avs\\"","x":1},'
             b'{"headline":"Short","a":1},{"headline":"Second long headline here today","k":2}]}')
        for n in (1, 7, 10000):
            s = news.Scan()
            for i in range(0, len(j), n):
                s.add(j[i:i + n])
            self.assertEqual(s.found, ["KRAKEN'S TOLVANEN SCORES TWICE, BEATS AVS", "SECOND LONG HEADLINE HERE TODAY"])

    def test_clean_keeps_font_characters(self):
        import news
        self.assertEqual(news.clean("Café — win #1 @ home"), "CAF - WIN 1 HOME")


class TestTickerFilter(unittest.TestCase):
    def test_mine_only(self):
        now = time.time()
        mine, other = game(), game()
        other["away"], other["home"] = "ZZZ", "YYY"
        allp = " ".join(p[0] for p in marquee_parts([(SEA_NFL, [mine, other])], now, True))
        only = " ".join(p[0] for p in marquee_parts([(SEA_NFL, [mine, other])], now, True, True))
        self.assertIn("ZZZ", allp)
        self.assertNotIn("ZZZ", only)


class Logos(unittest.TestCase):
    def test_every_team_has_a_logo(self):
        import logos
        import teams
        for sport, rows in teams.TEAMS.items():
            for row in rows:
                px = logos.get(sport, row[2])
                self.assertIsNotNone(px, (sport, row[0]))
                self.assertEqual(len(px), logos.SIZE * logos.SIZE)
                self.assertTrue(any(px), (sport, row[0]))  # not blank

    def test_unknown_team(self):
        import logos
        self.assertIsNone(logos.get("baseball", "ZZZ"))
        self.assertIsNone(logos.get("curling", "AAA"))


class EspnOrder(unittest.TestCase):
    """ESPN's soccer feed lists a team's score and records ('abbreviation': 'Total') before the team itself."""

    def test_records_before_team(self):
        import espn
        comp = (b'{"homeAway":"%s","winner":true,"score":"%s","records":[{"name":"All Splits","type":"total",'
                b'"abbreviation":"Total"}],"team":{"id":"%s","abbreviation":"%s"}}')
        rec = (b'{"shortName":"LAFC @ SEA","competitions":[{"competitors":[' + comp % (b"home", b"2", b"9", b"SEA") + b","
               + comp % (b"away", b"1", b"8", b"LAFC") + b'],"status":{"displayClock":"90","period":2,'
               b'"type":{"state":"post","shortDetail":"FT"}}}]}')
        g = espn.parse_event(rec, "2026-11-11T03:00Z", "soccer")
        self.assertEqual((g["home"], g["home_score"], g["away"], g["away_score"]), ("SEA", 2, "LAFC", 1))
        self.assertEqual(g["state"], "post")

    def test_team_before_score(self):
        import espn
        comp = b'{"homeAway":"%s","team":{"id":"%s","abbreviation":"%s"},"score":"%s"}'
        rec = (b'{"shortName":"KC @ SEA","competitors":[' + comp % (b"home", b"1", b"SEA", b"24") + b","
               + comp % (b"away", b"2", b"KC", b"17") + b'],"status":{"displayClock":"0:00","period":4,'
               b'"type":{"state":"post","shortDetail":"Final"}}}')
        g = espn.parse_event(rec, "2026-11-11T03:00Z", "football")
        self.assertEqual((g["home"], g["home_score"], g["away"], g["away_score"]), ("SEA", 24, "KC", 17))
