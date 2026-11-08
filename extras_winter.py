# Extra cameos (Sledding, SnowAngel, HotCocoa, IceSkater). Loaded only while one plays (see critters.EXTRAS).
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


class Sledding(Cameo):
    seasons = WINTER
    total = 230

    def slope(self, x):
        return 12 + min(x, 44) * 17 // 44

    def render(self, b, f):
        snowfall(b, f)
        for x in range(0, 64, 2):
            b.rect(x, self.slope(x), 2, 32, SNOW)
        b.rect(0, 29, 64, 3, dim(SNOW, 0.8))
        x = -10 + min(f, 170) * 74 // 150
        if 0 <= x < 64:
            ground = self.slope(x)
            b.rect(x, ground - 2, 11, 2, RED)                       # sled
            b.rect(x + 9, ground - 4, 2, 2, RED)
            b.rect(x + 3, ground - 8, 3, 3, SKIN)                  # kid
            b.rect(x + 2, ground - 5, 5, 3, (60, 120, 255))
            b.rect(x + 2, ground - 9, 5, 1, (255, 200, 40))
            b.rect(x + 7, ground - 6, 3, 1, (60, 120, 255))
            for k in range(4):
                b.rect(x - 2 - k * 3, ground - 1 + (k % 2), 2, 1, dim(WHITE, 0.7 - k * 0.15))
        if f > 90:
            caption(b, "WHEEE!", AMBER if (f // 5) % 2 else WHITE, 2)


class SnowAngel(Cameo):
    seasons = WINTER
    total = 220

    def render(self, b, f):
        snowfall(b, f)
        b.rect(0, 14, 64, 18, SNOW)
        b.rect(0, 14, 64, 1, dim(SNOW, 0.6))
        sweep = min(1.0, f / 110.0)
        ang = math.sin(sweep * 3.14159 * 4) * 0.5 + 0.5      # arms and legs open and close
        cx, cy = 32, 22
        shade = (190, 195, 215)
        # the imprint grows as the arms sweep
        reach = int(sweep * 10)
        for r in range(2, 3 + reach, 2):
            for k in range(8):
                a = k / 8.0 * 1.2
                b.rect(cx + int(math.cos(a) * r), cy - 2 + int(math.sin(a) * r * 0.9), 1, 1, shade)
                b.rect(cx - int(math.cos(a) * r), cy - 2 + int(math.sin(a) * r * 0.9), 1, 1, shade)
        b.rect(cx - 1, cy - 1, 3, 9, shade)
        if f < 160:   # the person making it
            b.rect(cx - 2, cy - 5, 4, 4, SKIN)
            b.rect(cx - 2, cy - 6, 4, 2, (60, 120, 255))
            b.rect(cx - 2, cy - 1, 4, 7, (60, 120, 255))
            arm = int(ang * 7)
            b.rect(cx - 3 - arm, cy, 3 + arm, 1, (60, 120, 255))
            b.rect(cx + 2, cy, 3 + arm, 1, (60, 120, 255))
            b.rect(cx - 2, cy + 6, 1 + arm // 2, 4, (60, 60, 120))
            b.rect(cx + 1, cy + 6, 1, 4, (60, 60, 120))
        else:
            b.rect(30, 2, 4, 1, WHITE)
            caption(b, "SNOW ANGEL", AMBER, 3)


class HotCocoa(Cameo):
    seasons = WINTER
    total = 220

    def render(self, b, f):
        b.rect(0, 28, 64, 4, (90, 60, 35))
        b.rect(22, 14, 16, 14, (240, 240, 240))
        b.rect(23, 15, 14, 3, (110, 60, 30))
        b.rect(38, 17, 4, 7, (240, 240, 240))
        b.rect(40, 18, 2, 5, (30, 30, 35))
        b.rect(24, 24, 12, 4, (230, 60, 60))
        for k in range(3):                      # marshmallows
            bob = int(math.sin(f / 7 + k * 2) * 1)
            b.rect(25 + k * 4, 13 + bob, 3, 3, WHITE)
        for k in range(3):                      # steam
            for j in range(7):
                x = 26 + k * 4 + int(math.sin(f / 9 + j * 0.8 + k) * 2)
                b.rect(x, 12 - j * 2 - (f // 4 + j) % 2, 1, 1, dim(WHITE, 0.7 - j * 0.09))
        if f > 90:
            caption(b, "AHHH..." if (f // 12) % 2 else "COZY", (255, 190, 120), 2)


class IceSkater(Cameo):
    seasons = WINTER
    total = 230

    def render(self, b, f):
        b.rect(0, 24, 64, 8, ICE)
        b.rect(0, 24, 64, 1, WHITE)
        for k in range(3):
            b.rect((k * 21 + f // 4) % 64, 27 + k, 6, 1, dim(WHITE, 0.6))
        t = f / 45.0
        x = 32 + int(math.sin(t) * 22)
        spin = f > 120
        lean = int(math.cos(t) * 2)
        b.rect(x - 1, 8, 4, 4, SKIN)
        b.rect(x - 1, 7, 4, 2, (255, 120, 180))
        b.rect(x - 2, 12, 6, 6, (255, 120, 180))
        if spin:
            w = 1 + abs(int(math.cos(f / 3) * 4))
            b.rect(x - w, 13, 2 * w + 3, 1, (255, 120, 180))
            b.rect(x - 1, 18, 4, 5, (255, 200, 220))
        else:
            b.rect(x - 5 + lean, 12 + (f // 6) % 2, 4, 1, (255, 120, 180))
            b.rect(x + 4 + lean, 13 - (f // 6) % 2, 4, 1, (255, 120, 180))
            b.rect(x - 1, 18, 2, 5, (255, 200, 220))
            b.rect(x + 1 + lean, 18, 2, 4, (255, 200, 220))
        b.rect(x - 2, 23, 6, 1, WHITE)
        if spin:
            for k in range(6):
                a = f / 2.5 + k
                b.rect(x + 1 + int(math.cos(a) * 9), 23 + int(math.sin(a) * 1), 1, 1, WHITE)
            caption(b, "TRIPLE!", AMBER, 2)
