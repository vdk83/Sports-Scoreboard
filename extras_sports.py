# Extra cameos (HockeyGoal, FieldGoal, Trophy). Loaded only while one plays (see critters.EXTRAS).
# (see critters.EXTRAS), so keep this file's imports small.
import math

from board import AMBER, WHITE, dim, text_width
from critters import YELLOW, Cameo, blob, hop, sprite

RED = (230, 40, 40)
BLUE = (60, 120, 255)
GREY = (150, 150, 160)
DARK = (25, 25, 35)
GREEN = (60, 190, 70)
BROWN = (140, 90, 40)
PINK = (255, 140, 170)
ORANGE = (255, 140, 0)


def stars(b, f, n=18):
    for k in range(n):
        if (f // 8 + k) % 7:
            b.rect((k * 37 + 5) % 64, (k * 13 + 3) % 28, 1, 1, dim(WHITE, 0.35 + 0.15 * (k % 3)))


def caption(b, s, c=AMBER, y=2):
    b.text((b.w - text_width(s)) // 2, y, s, c)
SKIN = (240, 200, 160)


class HockeyGoal(Cameo):
    day = False
    total = 210

    def render(self, b, f):
        b.rect(0, 22, 64, 10, (190, 220, 235))
        b.rect(0, 22, 64, 1, (110, 150, 185))
        b.rect(0, 20, 64, 2, (60, 60, 150))
        b.rect(44, 8, 18, 18, (210, 210, 215))                    # goal frame
        bulge = 2 if 90 <= f < 105 else 0
        b.rect(46, 10, 14 - bulge, 14, (25, 25, 35))
        for y in range(11, 24, 2):
            b.rect(46, y, 14 - bulge, 1, (90, 90, 100))
        for x in range(48, 60, 3):
            b.rect(x, 10, 1, 14, (90, 90, 100))
        # the player and the shot
        b.rect(6, 12, 4, 4, SKIN)
        b.rect(6, 11, 4, 2, RED)
        b.rect(5, 16, 6, 7, RED)
        b.rect(5, 23, 2, 4, DARK)
        b.rect(9, 23, 2, 4, DARK)
        swing = min(1.0, max(0.0, (f - 20) / 12))
        sx = int(11 + 4 * swing)
        b.rect(sx, 22, 6, 1, BROWN)
        b.rect(sx + 5, 18, 1, 5, BROWN)
        t = max(0, f - 32)
        px = 18 + min(t, 60) * 30 // 60
        if f >= 32 and px < 50:
            b.rect(px - 4, 25, 3, 1, dim(WHITE, 0.4))
        if f >= 32 and px < 56:
            b.rect(px, 24, 4, 2, DARK)
        elif f < 32:
            b.rect(17, 24, 4, 2, DARK)
        if f >= 90:
            on = (f // 4) % 2
            blob(b, 53, 4, (3, 5, 5), RED if on else (110, 20, 20))
            caption(b, "GOAL!", WHITE if on else AMBER, 3)
            for k in range(5):
                b.rect(20 + k * 9, 6 + (f // 3 + k * 5) % 8, 1, 1, YELLOW)


class FieldGoal(Cameo):
    total = 230

    def render(self, b, f):
        b.rect(0, 28, 64, 4, (30, 120, 45))
        b.rect(0, 28, 64, 1, WHITE)
        for x in (4, 14, 24):
            b.rect(x, 29, 1, 3, dim(WHITE, 0.5))
        b.rect(53, 16, 2, 12, YELLOW)         # the goal post
        b.rect(44, 15, 20, 2, YELLOW)
        b.rect(44, 3, 1, 12, YELLOW)
        b.rect(62, 3, 1, 12, YELLOW)
        # kicker
        leg = max(0.0, min(1.0, (f - 20) / 10))
        b.rect(6, 17, 4, 3, SKIN)
        b.rect(5, 20, 6, 5, BLUE)
        b.rect(5, 25, 2, 3, WHITE)
        b.rect(int(8 + 5 * leg), 25 - int(leg * 2), 4, 2, WHITE)
        t = f - 28
        if t < 0:
            bx, by = 14, 25
        else:
            u = min(1.0, t / 95.0)
            bx = 14 + int(u * 50)
            by = 25 - int(math.sin(u * 3.14159) * 21) + int(u * u * 4) if u < 1 else 99
        if by < 40:
            b.rect(bx, by, 5, 3, BROWN)
            b.rect(bx + 1, by + 1, 3, 1, WHITE)
        if f > 130:
            b.text(16, 20, "IT'S GOOD!", YELLOW if (f // 4) % 2 else WHITE)
            b.rect(44 + (f // 6) % 20, 2, 1, 1, WHITE)


class Trophy(Cameo):
    total = 210

    def render(self, b, f):
        gold = (255, 205, 60)
        shade = (200, 140, 20)
        cx = 32
        b.rect(cx - 6, 27, 13, 3, (110, 70, 30))
        b.rect(cx - 1, 20, 3, 7, shade)
        b.rect(cx - 5, 8, 11, 1, gold)
        blob(b, cx, 9, (11, 9, 9, 7, 5, 3), gold)
        b.rect(cx - 8, 10, 3, 1, gold)
        b.rect(cx - 8, 11, 1, 3, gold)
        b.rect(cx + 6, 10, 3, 1, gold)
        b.rect(cx + 8, 11, 1, 3, gold)
        b.rect(cx - 3, 10, 1, 4, WHITE if (f // 8) % 2 else (255, 240, 170))
        for k in range(6):
            t = (f * 2 + k * 31) % 90
            if t < 14:
                x = 10 + (k * 47) % 44
                y = 5 + (k * 11) % 20
                b.rect(x, y, 1, 3 if t % 4 < 2 else 1, WHITE)
                b.rect(x - 1, y + 1, 3, 1, WHITE if t % 4 < 2 else dim(WHITE, 0.5))
        if f > 40:
            caption(b, "CHAMPS!", YELLOW if (f // 5) % 2 else WHITE, 24 if False else 1)
