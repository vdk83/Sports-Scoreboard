# Extra cameos (Reindeer, Fireplace, SnowballFight, Icicles, NewYear). Loaded only while one plays (see critters.EXTRAS).
import math

from board import AMBER, WHITE, dim, text_width
from critters import SNOW, YELLOW, Cameo, blob, hop, snowfall, sprite

RED = (220, 40, 40)
BROWN = (140, 90, 40)
SKIN = (240, 200, 160)
DARK = (25, 25, 35)
ICE = (170, 215, 240)
WINTER = ("winter",)


def caption(b, s, c=AMBER, y=2):
    b.text((b.w - text_width(s)) // 2, y, s, c)


class Reindeer(Cameo):
    seasons = WINTER
    months = (12,)
    day = False
    total = 240
    DEER = ("B.B.....", ".BBBB..B", "..BBBBBB", "..BBBBBB", "..B..B..", "..B..B..")
    PAL = {"B": BROWN}

    def render(self, b, f):
        for k in range(14):
            b.rect((k * 17 + 5) % 64, (k * 7) % 14, 1, 1, dim(WHITE, 0.4 + 0.2 * (k % 3)))
        blob(b, 52, 6, (5, 7, 7, 5), (240, 240, 210))
        x = -50 + f * 130 // 240
        y = 12 + int(math.sin(f / 14) * 3)
        for k in range(3):
            sprite(b, x + 14 + k * 11, y + (k % 2), self.DEER, self.PAL)
            if k == 2:
                b.rect(x + 14 + k * 11 + 8, y + 1, 1, 1, RED if (f // 5) % 2 else (255, 120, 120))
        b.rect(x + 10, y + 3, 24, 1, (170, 140, 40))          # harness
        b.rect(x - 8, y + 4, 12, 4, RED)                       # sleigh
        b.rect(x - 9, y + 2, 2, 3, RED)
        b.rect(x - 8, y + 8, 14, 1, (170, 140, 40))
        b.rect(x - 4, y, 3, 4, (240, 240, 240))                # Santa
        b.rect(x - 4, y - 2, 3, 2, RED)
        for k in range(5):
            b.rect(x - 14 - k * 3, y + 7 + (k % 2), 1, 1, dim(YELLOW, 0.9 - k * 0.15))
        if f > 150:
            caption(b, "HO HO HO!", RED if (f // 6) % 2 else WHITE, 26)


class Fireplace(Cameo):
    seasons = WINTER
    day = False
    total = 230

    def render(self, b, f):
        b.rect(10, 8, 44, 24, (110, 50, 40))
        for y in range(8, 32, 4):
            b.rect(10, y, 44, 1, (80, 35, 30))
        b.rect(6, 6, 52, 3, (150, 110, 80))
        b.rect(20, 14, 24, 18, (15, 10, 10))
        b.rect(22, 29, 20, 3, (60, 35, 20))
        b.rect(24, 28, 16, 2, BROWN)
        for k in range(5):
            h = 7 + int((math.sin(f / 3 + k * 2.1) + 1) * 3)
            x = 24 + k * 4
            b.rect(x, 29 - h, 3, h, (255, 90, 20))
            b.rect(x + 1, 29 - h + 2, 1, h - 2, (255, 200, 40))
        for k in range(3):
            sx = 28 + k * 5
            sy = 14 - (f // 2 + k * 9) % 10
            if sy > 6:
                b.rect(sx, sy, 1, 1, (255, 180, 60))
        for k, c in enumerate((RED, (60, 190, 90), (240, 240, 240))):   # stockings
            x = 12 + k * 17 if k < 2 else 48
            b.rect(x, 9, 3, 5, c)
            b.rect(x, 13, 5, 2, c)
        if f > 100:
            caption(b, "COZY", (255, 190, 120), 1)


class SnowballFight(Cameo):
    seasons = WINTER
    total = 230
    PAL = {"W": SNOW, "K": DARK, "C": (255, 120, 0), "H": (90, 60, 160), "S": BROWN}
    MAN = (".HHH.", ".WWW.", "KWKWK" if False else "WKWKW", ".WCW.", "WWWWW", "WWWWW", ".WWW.")

    def render(self, b, f):
        snowfall(b, f)
        b.rect(0, 29, 64, 3, dim(SNOW, 0.5))
        sprite(b, 4, 19, self.MAN, self.PAL, scale=2)
        sprite(b, 49, 19, self.MAN, self.PAL, scale=2)
        for who, start in ((0, 20), (1, 70), (0, 120)):
            t = f - start
            if 0 <= t < 40:
                u = t / 40.0
                x = (16 + int(u * 32)) if who == 0 else (48 - int(u * 32))
                y = 20 - int(math.sin(u * 3.14159) * 14)
                b.rect(x, y, 3, 3, WHITE)
            if t == 40 or (40 < t < 46):
                x = 52 if who == 0 else 8
                for k in range(5):
                    b.rect(x + k * 2 - 4, 20 - (t - 40) * 2 + k % 2 * 3, 1, 1, WHITE)
        if 60 < f < 75 or 110 < f < 125:
            caption(b, "POOF!", AMBER, 2)


class Icicles(Cameo):
    seasons = WINTER
    total = 230

    def render(self, b, f):
        b.rect(0, 0, 64, 3, (130, 140, 170))
        b.rect(0, 29, 64, 3, SNOW)
        for k in range(9):
            x = 3 + k * 7
            grow = min(1.0, f / 70.0)
            ln = int((5 + (k * 5) % 9) * grow)
            for j in range(ln):
                w = 3 if j < ln // 2 else 1 if j < ln - 1 else 1
                b.rect(x + (3 - w) // 2, 3 + j, w, 1, ICE)
        # a drip from the longest one falls and splashes
        for n, kx in ((0, 24), (1, 45)):
            t = (f - 80 - n * 35) % 110
            if f > 80 and t < 40:
                y = 12 + t * t // 28
                if y < 28:
                    b.rect(kx, y, 1, 2, (150, 200, 255))
                else:
                    for k in range(4):
                        b.rect(kx - 3 + k * 2, 27 - (k % 2), 1, 1, (150, 200, 255))
        if f > 130:
            caption(b, "DRIP", ICE, 14)


class NewYear(Cameo):
    seasons = WINTER
    dates = (12, 30, 31)
    day = False
    total = 270
    COLORS = ((255, 90, 140), (90, 200, 255), (255, 220, 60), (150, 255, 120), (200, 130, 255))

    def render(self, b, f):
        b.rect(48, 4, 2, 28, (90, 90, 110))                  # the pole
        drop = min(f, 180)
        y = 3 + drop * 22 // 180
        if f < 195:
            blob(b, 49, y, (3, 5, 7, 7, 7, 5, 3), (230, 240, 255) if (f // 3) % 2 else (190, 205, 240))
            if (f // 4) % 2:
                b.rect(46, y + 3, 1, 1, WHITE)
                b.rect(52, y + 2, 1, 1, WHITE)
        if f < 180:
            n = 10 - f // 18
            b.text(18, 8, str(n), AMBER, 3 if n < 10 else 2)
            b.text(18, 22 if False else 24, "COUNTDOWN", dim(WHITE, 0.6))
        else:
            for k in range(26):
                t = f - 180
                x = (k * 29 + 7) % 64
                yy = (k * 7 + t * (1 + k % 3)) % 40 - 6
                if yy > 0:
                    b.rect(x, yy, 2, 2, self.COLORS[k % 5])
            caption(b, "HAPPY", YELLOW if (f // 5) % 2 else WHITE, 9)
            caption(b, "NEW YEAR!", YELLOW if (f // 5) % 2 else WHITE, 17)
