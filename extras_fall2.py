# Extra cameos (Mushrooms, Witch, Cauldron, Skeleton). Loaded only while one plays (see critters.EXTRAS).
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


class Mushrooms(Cameo):
    seasons = FALL
    total = 230

    def render(self, b, f):
        b.rect(0, 26, 64, 6, (60, 90, 35))
        for i, (x, h, c) in enumerate(((10, 7, RED), (22, 10, (230, 160, 60)), (35, 12, RED), (47, 8, (200, 120, 200)), (57, 6, RED))):
            t = f - i * 18
            if t < 0:
                continue
            g = min(1.0, t / 28.0)
            hh = max(1, int(h * g))
            b.rect(x, 26 - hh, 3, hh, (240, 235, 215))
            cap = max(2, int((h // 2 + 3) * g))
            blob(b, x + 1, 26 - hh - cap // 2, (cap - 2, cap, cap + 2)[:3], c)
            if c == RED and g > 0.8:
                b.rect(x, 26 - hh - 1, 1, 1, WHITE)
                b.rect(x + 2, 26 - hh - 2, 1, 1, WHITE)
        for k in range(10):
            b.rect((k * 23 + 5) % 64, 4 + (f * 2 + k * 9) % 22, 1, 2, (110, 160, 255))
        b.rect(0, 0, 64, 3, (90, 100, 125))
        if f > 140:
            caption(b, "POP!" if (f // 8) % 2 else "POP POP!", AMBER, 6)


class Witch(Cameo):
    seasons = FALL
    months = (10,)
    day = False
    total = 240
    PAL = {"P": (110, 50, 170), "K": DARK, "G": (80, 200, 80), "B": BROWN, "Y": YELLOW}
    WITCH = ("...PP....", "..PPPP...", ".PPPPPPP.", "PPPPPPPPP", "..GGG....", "..GKG....", "...G.....", ".PPPPP...", ".PPPPPP..")

    def render(self, b, f):
        stars(b, f)
        blob(b, 12, 7, (8, 12, 14, 14, 12, 8), (255, 235, 150))
        x = -26 + f * 100 // 240
        y = 14 + int(math.sin(f / 10) * 4)
        b.rect(x - 2, y + 11, 26, 2, BROWN)                    # broom
        for k in range(5):
            b.rect(x - 8 + k, y + 10 + k % 2, 6, 1, (200, 170, 70))
        sprite(b, x + 4, y - 6, self.WITCH, self.PAL, scale=2)
        for k in range(6):
            b.rect(x - 9 - k * 3, y + 11 + (k * 7 + f // 3) % 3, 1, 1, dim(WHITE, 0.8 - k * 0.12))
        if f > 140:
            caption(b, "HEHEHE!", (150, 255, 100), 26)


class Cauldron(Cameo):
    seasons = FALL
    months = (10,)
    day = False
    total = 230

    def render(self, b, f):
        b.rect(0, 29, 64, 3, (25, 20, 30))
        blob(b, 32, 17, (12, 18, 22, 24, 24, 22, 20, 16), (30, 30, 40))
        b.rect(21, 16, 22, 2, (60, 60, 75))
        b.rect(23, 14, 18, 3, (90, 230, 90))
        for k in range(5):
            t = (f * 2 + k * 31) % 90
            x = 24 + k * 4 + int(math.sin(t / 9 + k) * 2)
            y = 14 - t // 6
            if y > 0:
                r = 1 + (t % 18) // 9
                b.rect(x, y, r + 1, r + 1, (130, 255, 120) if t % 2 else (90, 230, 90))
        b.rect(26, 28, 4, 2, (255, 120, 20))
        b.rect(34, 28, 4, 2, (255, 120, 20))
        b.rect(30, 27, 4, 3, (255, 200, 40))
        if f > 90:
            caption(b, "BUBBLE" if (f // 10) % 2 else "TOIL", (150, 255, 100), 1)


class Skeleton(Cameo):
    seasons = FALL
    months = (10,)
    day = False
    total = 230
    BONE = (200, 200, 190)

    def render(self, b, f):
        stars(b, f)
        b.rect(0, 29, 64, 3, (20, 20, 25))
        x = 28
        beat = (f // 5) % 2
        bone = self.BONE
        b.rect(x, 2, 8, 7, bone)                              # skull
        b.rect(x + 1, 4, 2, 2, DARK)
        b.rect(x + 5, 4, 2, 2, DARK)
        b.rect(x + 3, 6, 2, 1, DARK)
        for j in range(3):
            b.rect(x + 1 + j * 3, 8, 1, 2, DARK)
        b.rect(x + 3, 9, 2, 3, bone)                           # neck
        for j in range(4):                                    # ribs
            b.rect(x - 1, 12 + j * 2, 10, 1, bone)
        b.rect(x + 3, 11, 2, 9, bone)
        b.rect(x, 20, 8, 2, bone)
        up = beat
        b.rect(x - 7, 12 - up * 4, 6, 1, bone)                 # arms
        b.rect(x - 7, 8 - up * 4 + 4, 1, 4, bone) if False else None
        b.rect(x + 9, 12 - (1 - up) * 4, 6, 1, bone)
        b.rect(x - 7, 9 - up * 4, 1, 4, bone)
        b.rect(x + 14, 9 - (1 - up) * 4, 1, 4, bone)
        b.rect(x + 1 - beat * 3, 22, 1, 7, bone)               # legs
        b.rect(x + 6 + (1 - beat) * 3, 22, 1, 7, bone)
        b.rect(x - beat * 3 - 1, 29, 3, 1, bone)
        b.rect(x + 6 + (1 - beat) * 3, 29, 3, 1, bone)
        if f > 40:
            b.text(46, 6, "SPOOKY" if (f // 12) % 2 else "BONES", ORANGE)
