# Extra cameos (Surfer, Sandcastle, Watermelon, Sailboat, Seagull). Loaded only while one plays (see critters.EXTRAS).
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


class Surfer(Cameo):
    seasons = SUMMER
    total = 240

    def render(self, b, f):
        waves(b, f, 20, 32, (20, 90, 170))
        x = -16 + f * 90 // 220
        y = 17 - int(math.sin(f / 12) * 3)
        # the wave under the board
        for k in range(12):
            h = 8 - abs(k - 5) * 2 // 2
            b.rect(x - 4 + k * 2, y + 3 + abs(k - 5) // 2, 3, max(1, h), (60, 150, 230))
            b.rect(x - 4 + k * 2, y + 3 + abs(k - 5) // 2, 3, 1, WHITE)
        b.rect(x, y + 1, 9, 1, (255, 200, 40))             # board
        b.rect(x + 3, y - 4, 3, 4, SKIN)                    # surfer
        b.rect(x + 3, y - 6, 3, 2, BROWN)
        b.rect(x + 2, y - 1, 5, 2, (255, 90, 90))
        b.rect(x - 1 + (f // 5) % 2 * 2, y - 3, 3, 1, SKIN)
        b.rect(x + 6 - (f // 5) % 2 * 2, y - 3, 3, 1, SKIN)
        if f > 190:
            caption(b, "COWABUNGA!" if False else "RADICAL!", AMBER, 2)


class Sandcastle(Cameo):
    seasons = SUMMER
    total = 240

    def render(self, b, f):
        b.rect(0, 25, 64, 7, SAND)
        grow = min(1.0, f / 100.0)
        cx = 32
        w = int(20 * grow)
        h = int(8 * grow)
        b.rect(cx - w // 2, 25 - h, w, h, (200, 165, 95))
        for k in range(4):                                  # towers
            tx = cx - 11 + k * 7
            th = int((6 + (k % 2) * 3) * grow)
            b.rect(tx, 25 - h - th, 4, th, (205, 170, 100))
            if grow > 0.9:
                b.rect(tx, 25 - h - th - 1, 1, 1, (205, 170, 100))
                b.rect(tx + 2, 25 - h - th - 1, 1, 1, (205, 170, 100))
        if grow >= 1:
            b.rect(cx, 6, 1, 5, DARK)
            b.rect(cx + 1, 6, 4, 3, RED)
        wave = f - 150
        if wave > 0:
            reach = min(wave, 40) if wave < 70 else max(0, 40 - (wave - 70))
            b.rect(0, 32 - reach // 2 - 1, 64, reach // 2 + 1, SEA)
            b.rect(0, 32 - reach // 2 - 1, 64, 1, WHITE)
            if wave > 40:
                b.rect(cx - w // 2, 25 - h, w, h, SAND if wave > 60 else (190, 160, 100))
                b.rect(cx - 11, 25 - h - 9, 24, 9, SAND if wave > 45 else (200, 165, 95))
        if f > 175:
            caption(b, "OH NO!", AMBER, 1)


class Watermelon(Cameo):
    seasons = SUMMER
    total = 220

    def render(self, b, f):
        b.rect(0, 29, 64, 3, (60, 150, 60))
        cx, cy = 20, 28
        for dy in range(-14, 1):
            hw = int((196 - dy * dy) ** 0.5)
            b.rect(cx - hw, cy + dy, hw * 2, 1, (40, 140, 60) if dy > -3 else (255, 70, 90))
        b.rect(cx - 13, cy - 2, 26, 1, (200, 255, 200))
        for sx, sy in ((-9, -6), (-4, -9), (2, -5), (7, -9), (-6, -3), (10, -4)):
            b.rect(cx + sx, cy + sy, 1, 2, DARK)
        b.rect(cx - 4, cy - 12, 2, 3, WHITE)                  # eyes
        b.rect(cx + 2, cy - 12, 2, 3, WHITE)
        b.rect(cx - 3, cy - 11, 1, 2, DARK)
        b.rect(cx + 3, cy - 11, 1, 2, DARK)
        open_mouth = 3 + (f // 7) % 3
        b.rect(cx + 7, cy - 9, 3, open_mouth, DARK)
        for k in range(5):                                    # spat seeds
            t = f - 30 - k * 16
            if 0 <= t < 60:
                b.rect(cx + 11 + t * 30 // 60, cy - 8 - int(math.sin(t / 60 * 3.14159) * 14), 2, 3, DARK)
            elif t >= 60:
                b.rect(cx + 11 + 30 + k * 3, 27 - k % 2, 2, 2, DARK)
        if f > 150:
            caption(b, "PTOO!" if (f // 8) % 2 else "SPIT!", AMBER, 3)


class Sailboat(Cameo):
    seasons = SUMMER
    total = 240

    def render(self, b, f):
        blob(b, 54, 5, (5, 7, 7, 5), YELLOW)
        waves(b, f, 22, 32, (30, 100, 190))
        x = -22 + f * 90 // 220
        y = 17 + int(math.sin(f / 10) * 1)
        b.rect(x + 2, y + 5, 14, 3, BROWN)
        b.rect(x + 1, y + 5, 1, 1, BROWN)
        b.rect(x + 16, y + 5, 1, 1, BROWN)
        b.rect(x + 9, y - 8, 1, 13, DARK)
        for j in range(10):                                  # main sail
            b.rect(x + 10, y - 7 + j, 1 + j * 5 // 9, 1, WHITE)
        for j in range(7):                                   # jib
            b.rect(x + 8 - j * 5 // 6, y - 4 + j, 1 + j * 5 // 6, 1, (255, 220, 220))
        b.rect(x + 9, y - 9, 3, 2, RED)
        # a gull
        gx = 64 - (f * 2) % 100
        if gx > -6 and f % 100 < 90 and f > 60:
            wing = (f // 5) % 2
            b.rect(gx, 6 + wing, 3, 1, WHITE)
            b.rect(gx + 3, 6 + 1 - wing, 3, 1, WHITE)
        if f > 190:
            caption(b, "AHOY!", AMBER, 3)


class Seagull(Cameo):
    seasons = SUMMER
    total = 230
    GULL = ("..WWW...", "WWWWWWWK", "WWWWWWWO", ".GGGGG..", "..O.O...")
    PAL = {"W": (240, 240, 245), "G": (160, 170, 185), "K": DARK, "O": (255, 160, 20)}

    def render(self, b, f):
        b.rect(0, 22, 64, 10, SAND)
        b.rect(0, 20, 64, 2, SEA)
        b.rect(40, 25, 7, 4, (200, 140, 60))               # the fries
        for k in range(4):
            b.rect(41 + k * 2, 22 - k % 2, 1, 4, YELLOW)
        if f < 90:
            gx = -16 + f * 60 // 90
            gy = 4 + int(math.sin(f / 10) * 2) + max(0, f - 40) // 4
            sprite(b, gx, gy, self.GULL, self.PAL, scale=2)
            wing = (f // 4) % 2
            b.rect(gx + 2, gy - 3 + wing * 2, 10, 2, WHITE)
        elif f < 130:
            u = f - 90
            sprite(b, 44 + u, 17 - u // 2, self.GULL, self.PAL, scale=2)
            b.rect(46 + u, 26 - u // 2, 1, 4, YELLOW)
        else:
            sprite(b, 70 - (f - 130) * 2 if False else 64, 0, self.GULL, self.PAL)
        if f > 100:
            caption(b, "MINE!", AMBER if (f // 5) % 2 else WHITE, 2)
