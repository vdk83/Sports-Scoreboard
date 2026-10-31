# Slideshow of every seasonal cameo, looping forever, with a title card before each.
# Run from your computer with:  mpremote run cameo_demo.py
import time

import critters
import interstate75
from board import AMBER, GREY, Board

i75 = interstate75.Interstate75(display=interstate75.DISPLAY_INTERSTATE75_64X32)
board = Board(i75.display, i75.width, i75.height)

NAMES = {"SnowmanWalk": "STROLL", "SnowmanOops": "OOPS", "Sprouts": "SPROUTS",
         "SunShades": "SHADES", "Pumpkin": "PUMPKIN",
         "PenguinSlide": "PENGUIN", "Butterfly": "BUTTERFLY", "IceCream": "ICE CREAM",
         "Fireflies": "FIREFLIES", "BeachBall": "BEACH BALL", "Leaves": "LEAVES",
         "GhostBat": "GHOST+BAT", "Turkey": "TURKEY",
         "Fireworks": "FIREWORKS", "XmasTree": "XMAS TREE", "Heart": "HEART", "Shamrock": "SHAMROCK",
         "HawkFly": "HAWK", "Flag12": "12 FLAG", "KrakenTentacle": "KRAKEN", "DodgerBall": "DODGERS"}

SHOWS = [(s.upper(), cs) for s, cs in critters.CAMEOS.items()]
SHOWS += [("HOLIDAY", critters.HOLIDAYS), ("TEAMS", critters.TEAMS)]

while True:
    for season, classes in SHOWS:
        for cls in classes:
            board.draw_message([(season, AMBER), (NAMES[cls.__name__], GREY)])
            i75.update()
            time.sleep(1.5)
            c = cls()
            while not c.done:
                c.draw(board)
                i75.update()
                time.sleep_ms(40)
