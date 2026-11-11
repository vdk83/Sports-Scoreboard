# Extra cameos (CatMouse, Dino, DogFetch, Pizza, Speaker, StatueOfLiberty, EmpireState). Loaded only while one plays (see critters.EXTRAS).
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


class CatMouse(Cameo):
    total = 200
    CAT = ("K.K.....", "KKKKK...", "KGKGKKKK", "KKKKKKKK", "KKKKKKKK", ".K.K.K.K")
    MOUSE = ("G.G.", "GGGGK", ".GGG.", "P.PP.")
    PAL = {"K": (70, 70, 85), "G": (190, 190, 200), "P": PINK}

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (80, 60, 40))
        b.rect(52, 20, 10, 10, DARK)   # mouse hole
        b.rect(54, 22, 6, 8, (5, 5, 5))
        mx = -10 + f * 72 // 150
        cx = mx - 22 + int(math.sin(f / 4) * 1)
        if mx < 54:
            sprite(b, mx, 22 - (f // 3) % 2, self.MOUSE, self.PAL, scale=2)
        if cx > -17:
            sprite(b, cx, 17 + (f // 3) % 2, self.CAT, self.PAL, scale=2)
            b.rect(cx - 6, 17 + (f // 6) % 2 * 2, 6, 2, self.PAL["K"])
        if f > 150:
            caption(b, "MEOW", AMBER, 4)


class Dino(Cameo):
    total = 230
    REX = ("......GGGG.", ".....GGKGGG", ".....GGGGGG", ".....GGGG..", "G....GGGGGG", "GG..GGGG.G.", "GGGGGGGG...", ".GGGGGGG...", "..GGGGG....", "..GG.GG....", "..G...G....")
    PAL = {"G": (90, 190, 80), "K": (20, 20, 20)}

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (110, 85, 50))
        x = -24 + f * 62 // 120 if f < 120 else 38 - 24 + 24 - 24
        x = -24 + min(f, 120) * 70 // 120
        step = (f // 5) % 2 if f < 120 else 0
        sprite(b, x, 8 + step, self.REX, self.PAL, scale=2)
        if f >= 120:
            roar = (f // 3) % 2
            b.rect(x + 22, 11 + roar, 5, 1, (240, 240, 240))
            caption(b, "RAWR!", (255, 80, 60) if roar else AMBER, 2)
            for k in range(3):
                b.rect(x + 28 + k * 4, 12 - roar * 2 + k, 1, 1, dim(WHITE, 0.6))
        if f < 120 and f % 30 < 4:
            b.rect(0, 30, 64, 1, (80, 60, 35))


class DogFetch(Cameo):
    total = 230
    DOG = ("......B.B.", "B.....BBBB", "BB.BBBBKBB", "BBBBBBBBBN", ".BBBBBBBP.", ".B.B..B.B.", ".B.B..B.B.")
    PAL = {"B": (190, 130, 70), "K": (20, 20, 20), "N": (30, 20, 20), "P": PINK}

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (50, 130, 50))
        bx = 8 + f * 40 // 100 if f < 100 else 48
        by = 27 - hop(f, 40, 14) if f < 100 else 27
        blob(b, bx + 1, by - 3, (3, 5, 5, 5, 3), (240, 240, 240))
        dx = 4 + (max(0, f - 15) * 42 // 100) if f < 115 else 46 - (f - 115) * 36 // 100
        flip = f >= 115
        step = (f // 4) % 2
        sprite(b, dx, 19 + step, self.DOG, self.PAL, flip=flip, scale=2)
        if f >= 115:
            blob(b, dx + 1, 23, (3, 5, 5, 5, 3), (240, 240, 240))
        if f > 170:
            caption(b, "GOOD DOG!", AMBER, 4)


class Pizza(Cameo):
    total = 200

    def render(self, b, f):
        cx, cy = 32, 17
        r = 9
        w = 1 + abs(int(math.cos(f / 14) * r))
        for dy in range(-r, r + 1):
            hw = int((r * r - dy * dy) ** 0.5)
            b.rect(cx - hw * w // r, cy + dy, max(1, hw * 2 * w // r), 1, (230, 160, 60) if abs(dy) > r - 2 else (250, 200, 80))
        for k, (px, py) in enumerate(((-4, -3), (3, -4), (-1, 1), (5, 2), (-5, 4), (2, 5))):
            if w * abs(px) // r < w:
                b.rect(cx + px * w // r, cy + py, max(1, 3 * w // r), 2, RED)
        if f > 80:
            caption(b, "YUM!" if (f // 10) % 2 else "SLICE!", AMBER, 25 if f > 100 else 2)


class Speaker(Cameo):
    day = False
    total = 220
    NOTE = ("..XX", "..X.", "..X.", "XX..", "XX..")

    def render(self, b, f):
        for k in range(9):
            h = 2 + int((math.sin(f / 4 + k * 1.7) + 1) * 8 * (0.4 + 0.6 * abs(math.sin(f / 31 + k))))
            b.rect(8 + k * 5, 30 - h, 4, h, (60, 220, 90) if h < 12 else (255, 200, 40) if h < 15 else RED)
        for n in range(4):
            t = (f * 2 + n * 40) % 160
            x = 6 + n * 14 + int(math.sin(t / 9) * 3)
            y = 26 - t // 7
            if y > 0:
                sprite(b, x, y, self.NOTE, {"X": [(255, 120, 200), (120, 200, 255), (255, 230, 90), (150, 255, 150)][n]})


def burst(b, cx, cy, t, c):
    """One firework: dots fly out from (cx, cy) for t = 0..15 frames, fading as they go."""
    if t < 0 or t > 15:
        return
    r = 1 + t * 5 // 8
    col = dim(c, 1.0 - t / 18)
    for k in range(8):
        a = k * math.pi / 4
        x, y = cx + int(math.cos(a) * r), cy + int(math.sin(a) * r * 0.8)
        if 0 <= x < 64 and 0 <= y < 28:
            b.rect(x, y, 1, 1, col)


class StatueOfLiberty(Cameo):
    total = 230
    LADY = ("..G.G.G....", "...GGGG....", "...GGGG....", "....GG.....", "..GGGGGG...", ".GGGGGGGG..",
            ".GGDGGGDG..", ".GGDGGGDG..", "..GDGGGDG..", "..GDGGGDG..", "..GGDGDGG..", "..GDGGGDG..",
            ".GGDGGGDGG.", ".GGDGGGDGG.", "GGDDGGGDDGG", "GGGGGGGGGGG")
    PAL = {"G": (70, 175, 145), "D": (35, 105, 90)}
    FIRE = ((255, 90, 90), (255, 230, 90), (110, 170, 255), (255, 255, 255))

    def render(self, b, f):
        x, y = 40, 5
        for yy in range(28, 32):
            b.rect(0, yy, 64, 1, (25, 70, 140) if (yy + f // 12) % 2 else (35, 90, 165))
        b.rect(x - 1, 21, 13, 7, (150, 150, 162))
        b.rect(x - 1, 21, 13, 1, (195, 195, 205))
        b.rect(x + 1, 24, 9, 1, (115, 115, 125))
        b.rect(x - 2, 27, 15, 1, (115, 115, 125))
        sprite(b, x, y, self.LADY, self.PAL)
        b.rect(x + 8, y - 3, 2, 6, self.PAL["G"])      # raised arm
        b.rect(x + 7, y - 4, 4, 1, (200, 170, 60))     # torch
        flame = (255, 230, 90) if (f // 3) % 2 else (255, 150, 30)
        b.rect(x + 8, y - 6, 2, 2, flame)
        if (f // 5) % 3:
            b.rect(x + 8, y - 7 if y - 7 >= 0 else 0, 2, 1, dim(flame, 0.5))
        for k, c in enumerate(self.FIRE):
            burst(b, 10 + (k * 7) % 22, 6 + (k * 5) % 9, (f - 30 - k * 45) % 120, c)
        if f > 110:
            b.text(3, 17, "NEW", AMBER)
        if f > 150:
            b.text(3, 24, "YORK", AMBER)


class EmpireState(Cameo):
    day = False
    total = 230
    SHOW = ((255, 60, 60), (240, 240, 240), (70, 130, 255), (70, 220, 100))
    TIERS = ((22, 10, 16), (16, 6, 12), (11, 5, 8), (8, 3, 6), (5, 3, 4), (3, 2, 2))   # y, height, width

    def render(self, b, f):
        stars(b, f, 10)
        for bx, bw, top in ((0, 7, 17), (7, 6, 21), (13, 5, 24), (46, 5, 23), (51, 6, 19), (57, 7, 15)):
            b.rect(bx, top, bw, 32 - top, (22, 22, 38))
            for wy in range(top + 2, 30, 3):
                for wx in range(bx + 1, bx + bw - 1, 2):
                    if (wx * 5 + wy * 3 + f // 40) % 4 == 0:
                        b.rect(wx, wy, 1, 1, (200, 170, 70))
        glow = self.SHOW[(f // 45) % 4]
        stone = (150, 150, 165)
        for i, (ty, th, tw) in enumerate(self.TIERS):
            c = stone if i < 2 else glow
            b.rect(32 - tw // 2, ty, tw, th, c)
            if i < 2:
                for wy in range(ty + 1, ty + th - 1, 2):
                    for wx in range(33 - tw // 2, 31 + tw // 2, 2):
                        if (wx * 7 + wy * 3 + f // 30) % 3:
                            b.rect(wx, wy, 1, 1, (255, 220, 110))
        b.rect(32, 0, 1, 3, (200, 200, 210))
        if (f // 10) % 2:
            b.rect(31, 0, 3, 1, RED)
        b.rect(0, 31, 64, 1, (50, 50, 60))
