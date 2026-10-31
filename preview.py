#!/usr/bin/env python3
"""See the scoreboard on your computer, no board needed.

    python3 preview.py cameos            # PNG of the middle frame of every cameo -> preview/
    python3 preview.py cameo Pumpkin     # live window of one cameo (needs pygame)
    python3 preview.py games             # PNG of sample live games in each layout -> preview/
    python3 preview.py clock             # PNG of the idle clock slide -> preview/

PNGs are written with pygame (headless); the live window needs a display.
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

import board  # noqa: E402
import critters  # noqa: E402
from scores import LEAGUES, make_view  # noqa: E402

W, H, SCALE = 64, 32, 10
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "preview")


class FakeG:
    """The bit of PicoGraphics that Board uses."""

    def __init__(self):
        self.surface = pygame.Surface((W, H))
        self.pen = (0, 0, 0)

    def create_pen(self, r, g, b):
        return (r, g, b)

    def set_pen(self, p):
        self.pen = p

    def rectangle(self, x, y, w, h):
        self.surface.fill(self.pen, (x, y, w, h))


def make():
    g = FakeG()
    return g, board.Board(g, W, H)


def save(g, name):
    os.makedirs(OUT, exist_ok=True)
    big = pygame.transform.scale(g.surface, (W * SCALE, H * SCALE))
    path = os.path.join(OUT, name + ".png")
    pygame.image.save(big, path)
    print(path)


def cameo_classes():
    seen = []
    for pool in list(critters.CAMEOS.values()) + [critters.HOLIDAYS, critters.TEAMS]:
        seen += [c for c in pool if c not in seen]
    return seen


def cameos():
    for cls in cameo_classes():
        g, b = make()
        c = cls()
        for _ in range(c.total // 2):
            c.draw(b)
        save(g, "cameo_" + cls.__name__)


SAMPLE = dict(sport="baseball", name="SF @ LAD", date="2026-10-25", away="SF", away_score=2, home="LAD",
              home_score=3, clock="", period=7, state="in", detail="Top 7th", bases=(True, False, True),
              outs=1, count="2-1", abs={"away": 1, "home": 2})
FOOT = dict(sport="football", name="KC @ SEA", date="2026-10-25", away="KC", away_score=17, home="SEA",
            home_score=24, clock="5:21", period=3, state="in", detail="5:21 - 3rd")
HOCKEY = dict(sport="hockey", name="VAN @ SEA", date="2026-10-25", away="VAN", away_score=1, home="SEA",
              home_score=2, clock="12:03", period=2, state="in", detail="12:03 - 2nd")


def games():
    now = time.time()
    pairs = [(LEAGUES[0], SAMPLE), (LEAGUES[1], FOOT), (LEAGUES[2], HOCKEY), (LEAGUES[0], SAMPLE)]
    for n in (1, 2, 3, 4):
        g, b = make()
        b.draw_games([make_view(l, gm, now) for l, gm in pairs[:n]])
        save(g, "games_%d" % n)


def clock():
    g, b = make()
    b.draw_clock((0, 24), "7:42", "P", "SAT OCT 31", ("rain", "54F"), 0)
    save(g, "clock")


def live(name):
    cls = {c.__name__: c for c in cameo_classes()}[name]
    pygame.display.init()
    os.environ.pop("SDL_VIDEODRIVER", None)
    screen = pygame.display.set_mode((W * SCALE, H * SCALE))
    g, b = make()
    c = cls()
    while not c.done:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return
        c.draw(b)
        screen.blit(pygame.transform.scale(g.surface, (W * SCALE, H * SCALE)), (0, 0))
        pygame.display.flip()
        time.sleep(0.03)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cameos"
    if cmd == "cameo":
        live(sys.argv[2])
    else:
        {"cameos": cameos, "games": games, "clock": clock}[cmd]()
