# Extra spring cameos (March to May). Loaded only while one plays (see critters.EXTRAS).
import math

from board import AMBER, WHITE, dim, text_width
from critters import YELLOW, Cameo, blob, hop, sprite

GREEN = (60, 170, 60)
PINK = (255, 140, 190)
SKIN = (240, 200, 160)
BROWN = (140, 90, 40)
DARK = (25, 25, 35)
SKY = ("spring",)
EGGS = ((255, 90, 140), (90, 170, 255), (255, 220, 60), (150, 230, 120), (190, 120, 255))


def caption(b, s, c=AMBER, y=2):
    b.text((b.w - text_width(s)) // 2, y, s, c)


def grass(b):
    b.rect(0, 28, 64, 4, (40, 130, 45))
    for x in range(1, 64, 5):
        b.rect(x, 27, 1, 1, (60, 170, 60))


class Bunny(Cameo):
    seasons = SKY
    months = (3, 4)
    total = 240
    BUN = ("..W.W....", "..W.W....", "..WWW....", ".WWWWW.WW", "WWWKWWWWW", "WWWWWWWW.", ".WWWWWW..", "..W..W...")
    PAL = {"W": (240, 240, 245), "K": (20, 20, 20)}

    def render(self, b, f):
        grass(b)
        x = -12 + f * 80 // 200
        jump = hop(f, 28, 9)
        sprite(b, x, 19 - jump, self.BUN, self.PAL, scale=2)
        for k in range(4):                              # eggs left behind
            ex = k * 15 + 6
            if ex < x - 4:
                c = EGGS[k % 5]
                blob(b, ex + 2, 24, (2, 4, 4, 4), c)
                b.rect(ex, 26, 5, 1, WHITE if k % 2 else dim(c, 0.6))
        if f > 190:
            caption(b, "HAPPY EASTER" if False else "HOP HOP!", AMBER, 3)


class FrogRain(Cameo):
    seasons = SKY
    total = 230
    FROG = (".G.G.", "GGGGG", "GKGKG", "GGGGG", "G...G")
    PAL = {"G": (70, 200, 70), "K": DARK}

    def render(self, b, f):
        b.rect(0, 0, 64, 7, (110, 120, 150))
        for k in range(14):
            x = (k * 23 + 7) % 64
            y = 6 + (f * 3 + k * 11) % 24
            b.rect(x, y, 1, 2, (110, 160, 255))
        b.rect(0, 28, 64, 4, (50, 100, 150))
        for k in range(3):                                   # puddle rings
            r = (f // 2 + k * 9) % 14
            b.rect(10 + k * 22 - r, 29, 2 * r + 2, 1, (130, 180, 230))
        x = 6 + f * 50 // 200
        j = hop(f, 36, 12)
        sprite(b, x, 21 - j, self.FROG, self.PAL, scale=2)
        if f > 190:
            caption(b, "RIBBIT!", (150, 255, 150), 9)


class Rainbow(Cameo):
    seasons = SKY
    total = 230
    BANDS = ((230, 40, 40), (255, 140, 0), (255, 220, 0), (60, 190, 70), (60, 120, 255), (150, 80, 220))

    def render(self, b, f):
        grow = min(1.0, f / 110.0)
        cx, cy = 32, 30
        for i, c in enumerate(self.BANDS):
            r = 26 - i * 2
            for x in range(-r, r + 1, 2):
                if (x + r) > 2 * r * grow:
                    break
                y = cy - int((r * r - x * x) ** 0.5)
                b.rect(cx + x, y, 2, 2, c)
        blob(b, 8, 24, (6, 10, 10, 8), WHITE)
        blob(b, 56, 24, (6, 10, 10, 8), WHITE)
        if f > 80:
            blob(b, 56, 2, (5, 7, 7, 5), YELLOW)
        if f > 130:
            caption(b, "OVER THE RAINBOW" if False else "WOW!", AMBER, 3)


class Bee(Cameo):
    seasons = SKY
    total = 240

    def render(self, b, f):
        grass(b)
        for i, x in enumerate((9, 27, 45)):
            b.rect(x, 20, 1, 8, (50, 150, 50))
            c = ((255, 90, 140), (255, 220, 60), (150, 120, 255))[i]
            b.rect(x - 2, 18, 5, 3, c)
            b.rect(x - 1, 17, 3, 5, c)
            b.rect(x, 19, 1, 1, (255, 200, 0) if i != 1 else (200, 90, 30))
        t = f / 40.0
        bx = 4 + int(f * 56 / 240)
        by = 12 + int(math.sin(t * 2.3) * 5)
        for k in range(10):                                  # dotted trail
            tt = (f - k * 4) / 40.0
            if f - k * 4 > 0:
                b.rect(4 + int((f - k * 4) * 56 / 240), 12 + int(math.sin(tt * 2.3) * 5), 1, 1, dim(WHITE, 0.55 - k * 0.05))
        b.rect(bx, by, 6, 4, (255, 200, 0))
        b.rect(bx + 1, by, 1, 4, DARK)
        b.rect(bx + 3, by, 1, 4, DARK)
        b.rect(bx + 5, by + 1, 1, 1, DARK)
        wing = (f // 2) % 2
        b.rect(bx + 1, by - 2 - wing, 3, 2, (200, 230, 255))
        if f > 190:
            caption(b, "BZZZ", AMBER, 3)


class Kite(Cameo):
    seasons = SKY
    total = 240

    def render(self, b, f):
        grass(b)
        kx = 40 + int(math.sin(f / 22) * 8)
        ky = 7 + int(math.sin(f / 31) * 2)
        sway = int(math.sin(f / 7) * 2)
        for i in range(0, 20):                               # string from the kid to the kite
            u = i / 19.0
            b.rect(int(14 + (kx - 14) * u), int(25 + (ky + 6 - 25) * u + math.sin(u * 3.14) * 2), 1, 1, dim(WHITE, 0.6))
        for j in range(7):                                   # diamond
            w = 1 + j if j < 4 else 7 - j
            b.rect(kx - w // 2 + 3, ky + j, w, 1, (230, 50, 60) if j % 2 == 0 else (255, 200, 60))
        for k in range(5):                                   # tail
            b.rect(kx + 3 + int(math.sin(f / 5 + k) * 2) + sway, ky + 7 + k * 2, 2, 1, (60, 190, 255) if k % 2 else (255, 120, 220))
        b.rect(12, 20, 4, 4, SKIN)                           # kid
        b.rect(12, 19, 4, 2, BROWN)
        b.rect(11, 24, 6, 4, (255, 140, 40))
        b.rect(12, 28, 2, 2, DARK)
        b.rect(15, 28, 2, 2, DARK)
        if f > 190:
            caption(b, "WHEEE!", AMBER, 2)


class Chick(Cameo):
    seasons = SKY
    total = 230

    def render(self, b, f):
        grass(b)
        wob = int(math.sin(f / 2) * 1) if 20 < f < 100 else 0
        egg = (250, 245, 230)
        if f < 110:
            blob(b, 32 + wob, 14, (4, 6, 8, 10, 10, 10, 8, 6), egg)
            if f > 50:
                b.rect(28 + wob, 20, 9, 1, DARK)
                if f > 80:
                    b.rect(31 + wob, 17, 3, 3, DARK)
        else:
            blob(b, 28, 24, (4, 6, 6), egg)                    # shell halves
            blob(b, 38, 24, (4, 6, 6), egg)
            y = 12 if f > 125 else 16
            blob(b, 33, y + 4, (6, 8, 8, 8, 6), YELLOW)
            blob(b, 33, y, (4, 6, 6), YELLOW)
            b.rect(31, y + 2, 1, 1, DARK)
            b.rect(35, y + 2, 1, 1, DARK)
            b.rect(33, y + 3, 2, 1, (255, 140, 0))
            b.rect(25, y + 5, 3, 1 + (f // 6) % 2, (255, 230, 120))
            b.rect(38, y + 5, 3, 1 + (f // 6 + 1) % 2, (255, 230, 120))
            if f > 140:
                caption(b, "PEEP!", AMBER, 2)


class Ladybug(Cameo):
    seasons = SKY
    total = 230

    def render(self, b, f):
        grass(b)
        b.rect(31, 8, 2, 20, (50, 150, 50))
        b.rect(26, 14, 5, 2, (50, 150, 50))
        b.rect(33, 19, 6, 2, (50, 150, 50))
        t = min(f, 130)
        if f < 150:
            by = 26 - t * 17 // 130
            wing = f > 130 and (f // 2) % 2
            blob(b, 32, by, (6, 8, 8, 6), (230, 40, 40))
            b.rect(32, by, 1, 4, DARK)
            b.rect(30, by + 1, 1, 1, DARK)
            b.rect(34, by + 2, 1, 1, DARK)
            b.rect(31, by - 2, 3, 2, DARK)
            if wing:
                b.rect(24, by - 2, 7, 2, (210, 230, 255))
                b.rect(34, by - 2, 7, 2, (210, 230, 255))
        else:
            u = f - 150
            x, y = 32 + u * 2, 9 - u // 5
            blob(b, x, y, (4, 6, 6, 4), (230, 40, 40))
            b.rect(x - 5, y - 2 - (f // 2) % 2, 4, 1, (210, 230, 255))
            b.rect(x + 2, y - 2 - (f // 2) % 2, 4, 1, (210, 230, 255))
        if f > 40 and f < 130:
            caption(b, "LADYBUG!" if False else "UP UP", AMBER, 2)
