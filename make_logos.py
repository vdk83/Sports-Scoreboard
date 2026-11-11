#!/usr/bin/env python3
"""Make logos_<sport>.py: a 10x10 pixel logo for every team in teams.py.

    python3 make_logos.py            (needs the internet and Pillow: pip install pillow)

Downloads each team's ESPN logo, shrinks it to SIZE x SIZE and stores 1 byte (RGB332) per pixel, in the order of
teams.TEAMS[sport]. Black means "transparent" (the panel is black anyway). Run it again after make_teams.py.
"""
import io
import json
import os
import urllib.request

from PIL import Image

import teams

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = 10
PATHS = {"baseball": "baseball/mlb", "football": "football/nfl", "hockey": "hockey/nhl",
         "basketball": "basketball/nba", "soccer": "soccer/usa.1"}
ESPN = "https://site.api.espn.com/apis/site/v2/sports/%s/teams?limit=60"


def fetch(url):
    return urllib.request.urlopen(url, timeout=30).read()


def convert(png):
    """SIZE x SIZE rows of (r, g, b): logo pixels brightened for the panel, black where the logo is see-through."""
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    box = img.getbbox()
    if box:
        img = img.crop(box)
    side = max(img.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    big = SIZE * 8  # shrink in two steps: average colours on premultiplied pixels, so edges don't go muddy
    sq = sq.resize((big, big), Image.LANCZOS)
    out = []
    for y in range(SIZE):
        for x in range(SIZE):
            r = g = b = a = 0
            for dy in range(8):
                for dx in range(8):
                    pr, pg, pb, pa = sq.getpixel((x * 8 + dx, y * 8 + dy))
                    r += pr * pa
                    g += pg * pa
                    b += pb * pa
                    a += pa
            if a < 255 * 64 * 0.45:  # less than 45% covered: leave it off
                out.append((0, 0, 0))
                continue
            r, g, b = r / a, g / a, b / a
            top = max(r, g, b)
            if top < 90:  # very dark pixels vanish on an LED panel: lift them to a dim grey-ish tone of the same hue
                k = 90 / max(top, 1)
                r, g, b = (min(235, c * k + 10) for c in (r, g, b))
            else:
                k = min(235 / top, 1.0) if top > 235 else 1.0
                r, g, b = r * k, g * k, b * k
            out.append((int(r), int(g), int(b)))
    return out


def main():
    for sport, path in PATHS.items():
        urls = {}
        for entry in json.loads(fetch(ESPN % path))["sports"][0]["leagues"][0]["teams"]:
            t = entry["team"]
            if t.get("logos"):
                urls[t["displayName"]] = t["logos"][0]["href"]
        data = bytearray()
        for row in teams.TEAMS[sport]:
            url = urls.get(row[0])
            if url:
                px = convert(fetch(url))
            else:
                print("no logo for", sport, row[0])
                px = [(0, 0, 0)] * (SIZE * SIZE)
            for r, g, b in px:
                v = (r >> 5) << 5 | (g >> 5) << 2 | b >> 6
                data.append(v if v or (r, g, b) == (0, 0, 0) else 0x24)  # 0 is "see-through": keep real dark pixels lit
        with open(os.path.join(HERE, "logos_%s.py" % sport), "w") as f:
            f.write("# Made by make_logos.py: %dx%d logos, 1 byte (RGB332) per pixel, in the order of teams.TEAMS[%r].\n"
                    % (SIZE, SIZE, sport))
            f.write("DATA = %r\n" % bytes(data))
        print(sport, len(teams.TEAMS[sport]), "logos")


if __name__ == "__main__":
    main()
