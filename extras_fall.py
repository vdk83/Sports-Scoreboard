# Extra cameos (Scarecrow, Squirrel, Geese, AppleDrop, HarvestMoon). Loaded only while one plays (see critters.EXTRAS).
import math

from board import AMBER, WHITE, dim, text_width
from critters import YELLOW, Cameo, blob, hop, sprite

FALL = ("fall",)
ORANGE = (255, 130, 20)
BROWN = (140, 90, 40)
SKIN = (240, 200, 160)
DARK = (25, 25, 35)
RED = (225, 45, 45)
GRASS = (70, 120, 40)


def caption(b, s, c=AMBER, y=2):
    b.text((b.w - text_width(s)) // 2, y, s, c)


def stars(b, f, n=20):
    for k in range(n):
        if (f // 9 + k) % 6:
            b.rect((k * 29 + 3) % 64, (k * 13 + 2) % 18, 1, 1, dim(WHITE, 0.4))


class Scarecrow(Cameo):
    seasons = FALL
    total = 240
    CROW = ("..KK..", ".KKKK.", "KKKKKO", ".KKK..", "..O.O.")
    PAL = {"K": (40, 40, 55), "O": (255, 170, 30)}

    def render(self, b, f):
        b.rect(0, 28, 64, 4, GRASS)
        b.rect(31, 12, 2, 18, BROWN)                        # post
        b.rect(21, 15, 22, 2, BROWN)                        # arms
        b.rect(26, 15, 12, 8, (200, 70, 50))                # shirt
        for k in range(3):                                  # straw sticking out
            b.rect(19 - k, 16 + k * 2, 2, 1, YELLOW)
            b.rect(43 + k, 16 + k * 2, 2, 1, YELLOW)
        b.rect(28, 7, 8, 8, (225, 190, 120))                # head (sack)
        b.rect(30, 9, 1, 2, DARK)
        b.rect(33, 9, 1, 2, DARK)
        b.rect(30, 12, 4, 1, DARK)
        b.rect(26, 5, 12, 2, (110, 70, 30))                 # hat
        b.rect(29, 1, 6, 4, (110, 70, 30))
        wave = (f // 8) % 2
        if wave:
            b.rect(44, 12, 3, 2, YELLOW)
        if 70 < f < 200:                                    # a crow lands on the hat
            cx = 64 - min(f - 70, 40) * 28 // 40 if f < 110 else 36
            cy = 0 if f >= 110 else 6 - (f - 70) // 8
            sprite(b, cx, max(-2, cy), self.CROW, self.PAL)
        if f > 120:
            b.text(46, 3, "CAW!", AMBER)


class Squirrel(Cameo):
    seasons = FALL
    total = 240
    SQ = ("....GGG", "GG.GGGK", "GGGGGGGO", ".GGGGGG.", "..GGGG..", "..G..G..")
    PAL = {"G": (170, 110, 60), "K": DARK, "O": (255, 150, 150)}

    def render(self, b, f):
        b.rect(0, 28, 64, 4, (80, 60, 35))
        for k in range(4):
            b.rect(k * 17 + 4, 27, 3, 1, (210, 120, 30))      # leaves
        x = -16 + min(f, 120) * 46 // 120
        step = (f // 4) % 2
        sprite(b, x, 19 + step - (0 if f < 120 else 0), self.SQ, self.PAL, scale=2)
        b.rect(x - 4, 12 + step, 5, 8, (170, 110, 60))        # the tail
        if f < 120:
            b.rect(x + 16, 24, 3, 3, BROWN)                    # acorn in hands
            b.rect(x + 16, 23, 3, 1, (110, 70, 30))
        else:
            dig = (f // 5) % 3
            b.rect(34 + dig, 27, 6, 1, (50, 35, 20))
            if f > 150:
                b.rect(38, 26, 3, 2, (110, 70, 30))
                for k in range(3):
                    b.rect(36 + k * 3, 26 - (f // 3 + k) % 3, 2, 2, (80, 60, 35))
        if f > 170:
            caption(b, "SAVED FOR WINTER" if False else "ACORN!", AMBER, 3)


class Geese(Cameo):
    seasons = FALL
    total = 240
    UP = ("W.....W", ".W...W.", "..WWW..", "...W...")
    DOWN = ("...K...", "..WWW..", ".W...W.", "W.....W")
    PAL = {"W": (225, 220, 205), "K": (60, 55, 55)}

    def render(self, b, f):
        for k in range(3):
            b.rect(k * 24 + 2, 28, 14, 1, (255, 170, 90))
        b.rect(0, 29, 64, 3, (80, 55, 40))
        x = -50 + f * 140 // 240
        for i, (dx, dy) in enumerate(((0, 0), (-11, 5), (-11, -5), (-22, 10), (-22, -10))):
            gx, gy = x + 40 + dx, 11 + dy + int(math.sin(f / 7 + i) * 1)
            sprite(b, gx, gy, self.UP if (f // 5 + i) % 2 else self.DOWN, self.PAL, scale=2)
        if f > 130:
            b.text(2, 3, "HONK!" if (f // 8) % 2 else "HONK HONK", AMBER)


class AppleDrop(Cameo):
    seasons = FALL
    total = 230

    def render(self, b, f):
        b.rect(0, 28, 64, 4, GRASS)
        b.rect(28, 12, 6, 17, BROWN)                          # trunk
        blob(b, 31, 1, (16, 24, 28, 28, 24, 16), (60, 140, 50))
        for k, (ax, ay) in enumerate(((20, 8), (40, 9), (26, 14))):
            if not (k == 0 and f > 60):
                blob(b, ax, ay, (3, 5, 5, 3), RED)
        if f <= 60:
            ay = 8
        else:
            t = f - 60
            ay = min(24, 8 + t * t // 12)
        if f > 60:
            blob(b, 20, ay, (3, 5, 5, 3), RED)
            b.rect(20, ay - 1, 1, 1, BROWN)
        if f > 100:                                          # a worm pokes out
            up = min(5, (f - 100) // 4)
            b.rect(20, 28 - up, 2, up, (255, 160, 190))
            b.rect(21, 28 - up, 1, 1, DARK)
        if 70 < f < 95:
            caption(b, "THUD!", AMBER, 2)
        if f > 150:
            caption(b, "HI!", WHITE, 2)


class HarvestMoon(Cameo):
    seasons = FALL
    day = False
    total = 240

    def render(self, b, f):
        stars(b, f)
        y = 26 - min(f, 150) * 19 // 150
        blob(b, 32, y, (8, 12, 14, 14, 14, 14, 12, 8), (255, 170, 60))
        b.rect(28, y + 3, 3, 2, (230, 140, 40))
        b.rect(35, y + 5, 2, 2, (230, 140, 40))
        b.rect(0, 27, 64, 5, (10, 15, 10))
        for k in range(6):                                    # field of corn
            x = 5 + k * 11
            b.rect(x, 20, 2, 9, (15, 30, 15))
            b.rect(x - 2, 21 + k % 2, 2, 1, (15, 30, 15))
            b.rect(x + 2, 22 - k % 2, 2, 1, (15, 30, 15))
        ox = 52
        b.rect(ox, 14, 5, 5, (30, 25, 20))                     # owl on a post
        b.rect(ox + 1, 12, 3, 2, (30, 25, 20))
        b.rect(ox + 1, 15, 1, 1, YELLOW if (f // 40) % 4 else (30, 25, 20))
        b.rect(ox + 3, 15, 1, 1, YELLOW if (f // 40) % 4 else (30, 25, 20))
        b.rect(ox + 2, 19, 1, 8, (30, 25, 20))
        if f > 150:
            caption(b, "HOOT!" if (f // 10) % 2 else "HOO HOO", AMBER, 2)
