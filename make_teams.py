#!/usr/bin/env python3
"""Make teams.py: every MLB, NFL and NHL team the settings page can follow.

    python3 make_teams.py

Reads team names, abbreviations and colours from ESPN and MLB's Stats API (needs the internet) and writes
teams.py next to this script. Run it again after a team moves or is added, then deploy.
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ESPN = "https://site.api.espn.com/apis/site/v2/sports/%s/teams?limit=60"
MLB = "https://statsapi.mlb.com/api/v1/teams?sportId=1&fields=teams,id,name,abbreviation,active"
LEAGUES = (("baseball", "baseball/mlb"), ("football", "football/nfl"), ("hockey", "hockey/nhl"),
           ("basketball", "basketball/nba"), ("soccer", "soccer/usa.1"))


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=30))


def led(hexcolor):
    """(r, g, b) scaled so the panel shows it brightly, plus how colourful it is (0..1)."""
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))
    top = max(r, g, b)
    if top == 0:
        return (0, 0, 0), 0.0
    k = 235.0 / top
    return (int(r * k), int(g * k), int(b * k)), (top - min(r, g, b)) / top


KEEP = {("baseball", "LAD"): (0, 110, 255), ("football", "SEA"): (105, 220, 40),
        ("hockey", "SEA"): (70, 210, 230),
        ("soccer", "SEA"): (105, 220, 40)}  # the colours the board already used for the original three teams


FEED_ABBR = {("hockey", "UTAH"): "UTA"}  # where the scoreboard feed spells a team differently from the teams list


def pick_color(team):
    """The colour that shows best on the panel: colourful and bright (dark navy is hard to see)."""
    cands = []
    for key in ("color", "alternateColor"):
        c, sat = led(team.get(key) or "000000")
        cands.append((c, sat, 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]))
    good = [c for c in cands if c[1] >= 0.3]
    return max(good, key=lambda c: c[2])[0] if good else cands[0][0]


def main():
    mlb = {t["name"]: t for t in get(MLB)["teams"] if t.get("active", True)}
    out = {}
    for sport, path in LEAGUES:
        rows = []
        for entry in get(ESPN % path)["sports"][0]["leagues"][0]["teams"]:
            t = entry["team"]
            abbr, mlb_id = t["abbreviation"], 0
            abbr = FEED_ABBR.get((sport, abbr), abbr)
            if sport == "baseball":
                m = mlb.get(t["displayName"])
                if m is None:
                    raise SystemExit("no MLB match for " + t["displayName"])
                abbr, mlb_id = m["abbreviation"], m["id"]  # MLB's own abbreviation is what its games use
            rows.append((t["displayName"], t["name"].upper(), abbr, t["abbreviation"].lower(),
                         KEEP.get((sport, abbr)) or pick_color(t), mlb_id))
        rows.sort()
        out[sport] = rows
    with open(os.path.join(HERE, "teams.py"), "w") as f:
        f.write("# Made by make_teams.py: every team the settings page can follow.\n")
        f.write("# (full name, nickname, abbreviation in the game feeds, ESPN page name, (r, g, b), MLB team id)\n")
        f.write("TEAMS = {\n")
        for sport, rows in out.items():
            f.write("    %r: (\n" % sport)
            for r in rows:
                f.write("        %r,\n" % (r,))
            f.write("    ),\n")
        f.write("}\n")
    print({s: len(r) for s, r in out.items()}, "-> teams.py")


main()
