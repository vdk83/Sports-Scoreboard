# Extra cameos (Crab, ShootingStar, Lemonade, Palm, Campfire). Loaded only while one plays (see critters.EXTRAS).
import math

from board import AMBER, WHITE, dim, text_width
from critters import YELLOW, Cameo, blob, hop, sprite

SUMMER = ("summer",)
SAND = (225, 195, 120)
SEA = (30, 110, 200)
SKIN = (240, 200, 160)
BROWN = (140, 90, 40)
DARK = (25, 25, 35)
RED = (230, 50, 50)
GREEN = (60, 170, 60)


def caption(b, s, c=AMBER, y=2):
    b.text((b.w - text_width(s)) // 2, y, s, c)


def waves(b, f, y0, y1, c=SEA):
    b.rect(0, y0, 64, y1 - y0, c)
    for k in range(6):
        x = (k * 13 + f // 2) % 70 - 6
        b.rect(x, y0 + 1 + k % 3 * 2, 5, 1, dim(WHITE, 0.6))


class Crab(Cameo):
    seasons = SUMMER
    total = 230
    CRAB = ("R.R....R.R", "RR.RRRR.RR", ".RRRRRRRR.", "RRKRRRRKRR", ".R.R..R.R.")
    PAL = {"R": (235, 70, 50), "K": DARK}

    def render(self, b, f):
        b.rect(0, 22, 64, 10, SAND)
        b.rect(0, 20, 64, 2, SEA)
        for k in range(3):
            b.rect(8 + k * 22 + (f // 10) % 2, 28, 3, 1, (190, 160, 100))
        x = 8 + int(math.sin(f / 18) * 24)
        snap = (f // 6) % 2
        sprite(b, x, 19, self.CRAB, self.PAL, scale=2)
        b.rect(x - 4, 14 - snap * 2, 4, 4, self.PAL["R"])
        b.rect(x + 20, 14 - (1 - snap) * 2, 4, 4, self.PAL["R"])
        if f > 100 and f % 60 < 30:
            caption(b, "SNIP!" if snap else "SNAP!", AMBER, 3)


class ShootingStar(Cameo):
    seasons = SUMMER
    day = False
    total = 240

    def render(self, b, f):
        for k in range(28):
            if (f // 10 + k) % 6:
                b.rect((k * 31 + 3) % 64, (k * 17 + 2) % 26, 1, 1, dim(WHITE, 0.35 + 0.12 * (k % 4)))
        b.rect(0, 28, 64, 4, (10, 15, 30))
        for n, start in enumerate((20, 100, 170)):
            t = f - start
            if 0 <= t < 40:
                x = 64 - t * 2 - n * 8
                y = 2 + t // 2 + n * 3
                for k in range(8):
                    b.rect(x + k * 2, y - k, 2, 1, dim(WHITE, 1.0 - k * 0.11))
                b.rect(x, y, 2, 2, WHITE)
        if f > 60:
            caption(b, "MAKE A WISH", (200, 220, 255), 26)


class Lemonade(Cameo):
    seasons = SUMMER
    total = 220

    def render(self, b, f):
        b.rect(0, 29, 64, 3, (150, 100, 50))
        fill = min(1.0, f / 80.0)
        b.rect(24, 8, 14, 21, (210, 235, 245))
        b.rect(25, 9, 12, 19, (15, 25, 50))
        h = int(17 * fill)
        b.rect(25, 28 - h, 12, h, (255, 235, 90))
        for k in range(3):                                   # ice cubes
            if fill > 0.6:
                b.rect(26 + k * 4, 11 + (f // 9 + k) % 2 * 1 + (28 - h > 12) * 0, 3, 3, (220, 240, 255))
        b.rect(33, 3, 2, 18, (255, 90, 120))               # straw
        b.rect(33, 3, 6, 2, (255, 90, 120))
        for k in range(3):                                   # lemon slice
            b.rect(36, 8 + k, 5 - k * 2 + 2, 1, YELLOW)
        if fill < 1.0:
            b.rect(44, 0, 2, 6 + int(fill * 10) % 4, YELLOW)
        if f > 120:
            b.text(44, 10, "ICE", (150, 220, 255))
            b.text(44, 17, "COLD", (150, 220, 255) if (f // 10) % 2 else AMBER)


class Palm(Cameo):
    seasons = SUMMER
    total = 230

    def render(self, b, f):
        b.rect(0, 28, 64, 4, SAND)
        sway = int(math.sin(f / 12) * 2)
        for j in range(18):                                  # curved trunk
            b.rect(30 + int(j * j / 70) + sway * j // 18, 27 - j, 3, 1, (140, 95, 50))
        tx = 30 + int(17 * 17 / 70) + sway
        top = 27 - 17
        for k, (dx, dy) in enumerate(((-9, 3), (-6, 0), (-3, -2), (4, -2), (7, 0), (10, 3))):
            for s in range(1, 5):
                b.rect(tx + 1 + dx * s // 4, top + dy * s // 4 + s // 2, 3, 1, GREEN)
        c = f - 70
        if 0 <= c < 40:                                      # a coconut drops
            y = top + 3 + c * c // 25
            b.rect(tx + 3, min(y, 25), 3, 3, (110, 70, 35))
        if c >= 40:
            b.rect(tx + 3, 25, 3, 3, (110, 70, 35))
            if c < 70:
                caption(b, "BONK!", AMBER, 3)
        else:
            b.rect(tx + 3, top + 3, 3, 3, (110, 70, 35)) if c < 0 else None
        blob(b, 52, 5, (5, 7, 7, 5), YELLOW)


class Campfire(Cameo):
    seasons = SUMMER
    day = False
    total = 230

    def render(self, b, f):
        for k in range(18):
            if (f // 9 + k) % 5:
                b.rect((k * 29 + 4) % 64, (k * 11 + 1) % 20, 1, 1, dim(WHITE, 0.4))
        b.rect(0, 29, 64, 3, (30, 50, 30))
        b.rect(24, 27, 16, 2, BROWN)
        b.rect(26, 26, 12, 2, (110, 70, 35))
        for k in range(5):
            h = 6 + int((math.sin(f / 3 + k * 2) + 1) * 3)
            b.rect(27 + k * 2, 26 - h, 3, h, (255, 90, 20))
            b.rect(28 + k * 2, 26 - h + 2, 1, h - 2, (255, 210, 60))
        for k in range(4):
            y = 20 - (f // 2 + k * 7) % 18
            b.rect(26 + k * 4 + int(math.sin(f / 6 + k) * 2), y, 1, 1, (255, 190, 80))
        b.rect(40, 10, 14, 1, BROWN)                          # marshmallow stick
        b.rect(40 + 12, 9 + (f // 14) % 2, 3, 3, WHITE if f < 120 else (150, 100, 40))
        if f > 120:
            caption(b, "S'MORES!", AMBER, 2)
