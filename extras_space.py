# Extra cameos (Rocket, Ufo, Robot, Pacman, Invaders). Loaded only while one plays (see critters.EXTRAS).
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


class Rocket(Cameo):
    day = False
    total = 230
    SHIP = ("..R..", ".WWW.", ".WLW.", ".WWW.", ".WWW.", "RWWWR", "R.W.R")
    PAL = {"R": RED, "W": (235, 235, 245), "L": (90, 170, 255)}

    def render(self, b, f):
        stars(b, f)
        b.rect(24, 30, 16, 2, (70, 70, 80))
        lift = max(0, f - 75)
        y = 16 - lift * lift // 70
        if f < 75:
            s = str(3 - f // 25)
            b.text(30, 4, s, AMBER, 2)
        if f >= 60:
            fl = 3 + (f // 2) % 4 + min(8, lift // 3)
            b.rect(30, y + 14, 4, fl, ORANGE)
            b.rect(31, y + 14, 2, fl + 2, YELLOW)
        if f >= 70 and y < 26:
            for k in range(6):
                w = 3 + k * 2 + (f // 3) % 2
                b.rect(32 - w // 2, min(31, 29 - k), w, 1, dim(GREY, 0.7 - k * 0.1))
        if y > -15:
            sprite(b, 27, y, self.SHIP, self.PAL, scale=2)
        if f > 130:
            caption(b, "LIFTOFF!")


class Ufo(Cameo):
    day = False
    total = 240
    COW = ("W.....KK", "WKWWWWWW", "WWWWKWWW", "W.W..W.W")
    PAL = {"W": (240, 240, 240), "K": (30, 30, 30)}

    def render(self, b, f):
        stars(b, f, 12)
        b.rect(0, 29, 64, 3, (20, 60, 25))
        x = min(30, -12 + f * 42 // 60) if f < 150 else 30 + (f - 150) * 2
        y = 5 + int(math.sin(f / 9) * 1)
        beam = 60 <= f < 150
        cow = 21 if f < 70 else max(9, 21 - (f - 70) * 12 // 80) if f < 150 else 9
        if beam:
            for yy in range(y + 4, 29, 2):
                w = 6 + (yy - y) // 2
                b.rect(x - w // 2 + 4, yy, w, 1, (90, 110, 40))
        if f < 150:
            sprite(b, 22, cow, self.COW, self.PAL, scale=2)
        elif f < 185:
            sprite(b, 22 + (f - 150) * 2, 21, self.COW, self.PAL, flip=True, scale=2)
        blob(b, x + 4, y, (4, 8, 10), (170, 175, 195))
        b.rect(x + 1, y - 1, 6, 1, (120, 220, 240))
        for k in range(3):
            if (f // 4 + k) % 3 == 0:
                b.rect(x + 1 + k * 3, y + 3, 1, 1, YELLOW)
        if 100 < f < 150:
            caption(b, "MOO?", WHITE, 22)


class Robot(Cameo):
    total = 220
    BODY = ("..K..", ".KGK.", ".GRG.", "GGGGG", "GBGBG", "GGGGG", ".G.G.", ".K.K.")
    ARM = ("G", "G", "G")
    PAL = {"K": (60, 60, 70), "G": (170, 175, 190), "R": (255, 60, 60), "B": (90, 200, 255)}

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (50, 50, 60))
        x = -12 + f * 38 // 40 if f < 40 else 26
        dance = f >= 50
        lift = 2 if dance and (f // 6) % 2 else 0
        y = 14 - lift
        sprite(b, x, y, self.BODY, self.PAL, scale=2)
        g = self.PAL["G"]
        if dance:
            a = (f // 4) % 2
            b.rect(x - 3, y + 8 - (a * 6), 3, 2, g)
            b.rect(x - 3, y + 6 - (a * 6), 2, 4, g)
            b.rect(x + 10, y + 8 - ((1 - a) * 6), 3, 2, g)
            b.rect(x + 11, y + 6 - ((1 - a) * 6), 2, 4, g)
            caption(b, "BEEP" if (f // 8) % 2 else "BOOP", (120, 220, 255) if (f // 8) % 2 else (255, 150, 220), 3)
        else:
            b.rect(x - 2, y + 8, 2, 2, g)
            b.rect(x + 10, y + 8, 2, 2, g)


class Pacman(Cameo):
    day = False
    total = 230

    def render(self, b, f):
        lane = 16
        x = -8 + f * 2 // 1 % 100 if f < 160 else 0
        px = -8 + f * 76 // 160
        for k in range(10):
            dx = 4 + k * 7
            if dx > px + 2 or px > 80:
                b.rect(dx, lane, 1, 1, (255, 220, 160))
        b.rect(0, lane - 5, 64, 1, (30, 30, 200))
        b.rect(0, lane + 5, 64, 1, (30, 30, 200))
        mouth = (f // 3) % 3
        blob(b, px + 3, lane - 3, (3, 5, 6, 6, 6, 5, 3), YELLOW)
        if mouth:
            b.rect(px + 4, lane - 1, 4 if mouth == 2 else 3, 1 + (mouth == 2), (0, 0, 0))
        gx = px + 14
        if gx < 70:
            for j, w in enumerate((4, 6, 6, 6, 6, 6)):
                b.rect(gx + 3 - w // 2, lane - 3 + j, w, 1, RED)
            b.rect(gx, lane + 3, 1, 1, RED)
            b.rect(gx + 2, lane + 3, 1, 1, RED)
            b.rect(gx + 4, lane + 3, 1, 1, RED)
            b.rect(gx + 1, lane - 1, 2, 2, WHITE)
            b.rect(gx + 4, lane - 1, 2, 2, WHITE)
            b.rect(gx + 2, lane, 1, 1, BLUE)
            b.rect(gx + 5, lane, 1, 1, BLUE)
        if f > 175:
            caption(b, "WAKA WAKA", YELLOW, 26)


class Invaders(Cameo):
    day = False
    total = 240
    A = ("..X.....X..", "...X...X...", "..XXXXXXX..", ".XX.XXX.XX.", "XXXXXXXXXXX", "X.XXXXXXX.X", "X.X.....X.X", "...XX.XX...")
    B = ("..X.....X..", "X..X...X..X", "X.XXXXXXX.X", "XXX.XXX.XXX", "XXXXXXXXXXX", ".XXXXXXXXX.", "..X.....X..", ".X.......X.")

    def render(self, b, f):
        sway = int(math.sin(f / 22) * 10)
        dead = max(0, (f - 100) // 20)
        for row in range(2):
            for col in range(4):
                if row * 4 + col < dead:
                    continue
                x = 3 + col * 15 + sway + 3
                y = 3 + row * 9 + f // 40
                sprite(b, x, y, self.A if (f // 14) % 2 else self.B, {"X": (80, 255, 120) if row else (255, 120, 255)})
        sx = 31
        b.rect(sx - 2, 28, 5, 2, (80, 200, 255))
        b.rect(sx - 1, 27, 3, 1, (80, 200, 255))
        if 80 <= f < 200:
            shot = (f - 80) % 20
            b.rect(sx, 27 - shot * 2, 1, 3, WHITE)
        if f > 190:
            caption(b, "GAME OVER?", RED, 26)
