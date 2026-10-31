# Plays each score animation on the panel so you can see them without a live game.
# Run from your computer with:  mpremote run demo.py
import time

import interstate75
from board import Anim, Board
from scores import LEAGUES, banner, make_view

i75 = interstate75.Interstate75(display=interstate75.DISPLAY_INTERSTATE75_64X32)
board = Board(i75.display, i75.width, i75.height)
NOW = time.time()

BASEBALL = dict(sport="baseball", name="SF @ LAD", date="2026-10-25", away="SF", away_score=2,
                home="LAD", home_score=3, clock="", period=7, state="in", detail="Top 7th",
                bases=(True, False, True), outs=1, count="2-1", abs={"away": 1, "home": 2})
BASES_LOADED = dict(BASEBALL, detail="Bottom 8th", bases=(True, True, True), outs=2, count="3-2",
                    abs={"away": 0, "home": 1})
FOOTBALL = dict(sport="football", name="KC @ SEA", date="2026-10-25", away="KC", away_score=17,
                home="SEA", home_score=24, clock="5:21", period=3, state="in", detail="5:21 - 3rd")
HOCKEY = dict(sport="hockey", name="VAN @ SEA", date="2026-10-25", away="VAN", away_score=1,
              home="SEA", home_score=2, clock="12:03", period=2, state="in", detail="12:03 - 2nd")

# (league, [games shown], index of the game that scores, side that scores, points)
SAMPLES = [
    (LEAGUES[0], [BASEBALL], 0, "home", 1),
    (LEAGUES[0], [BASES_LOADED], 0, "home", 4),
    (LEAGUES[0], [BASEBALL, FOOTBALL], 0, "home", 1),
    (LEAGUES[1], [FOOTBALL], 0, "home", 7),
    (LEAGUES[2], [HOCKEY], 0, "home", 1),
    (LEAGUES[1], [FOOTBALL], 0, "away", 3),
]

for league, games, idx, side, delta in SAMPLES:
    g = games[idx]
    views = [make_view(league if gm is g else LEAGUES[1], gm, NOW) for gm in games]
    board.draw_games(views)
    i75.update()
    time.sleep(3)
    text, ours = banner(league, g, side, delta)
    a = Anim("demo", league["sport"], league["color"] if ours else (110, 110, 110), text, ours)
    region = board.regions(len(games))[idx]
    while not a.done:
        board.draw_games(views)
        board.draw_anim(a, region)
        i75.update()
        a.frame += 1
        time.sleep_ms(30)
    board.draw_games(views)
    i75.update()
    time.sleep(2)
print("demo done")

# Seasonal cameos: every one, regardless of the time of year.
import critters
for cls in [c for cs in critters.CAMEOS.values() for c in cs]:
    c = cls()
    while not c.done:
        c.draw(board)
        i75.update()
        time.sleep_ms(40)
print("cameos done")
