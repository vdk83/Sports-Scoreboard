# Seasonal cameos for the idle screen: a snowman strolls by, a pumpkin hops in, etc.
# Each cameo draws the whole panel for a few seconds, one frame per draw() call.
#
# Only needs a Board (rect/clear/text), so it can be previewed off the board too.
import math
import random

from board import AMBER, WHITE, dim, text_width

SNOW = (230, 230, 245)
FLAKE = (120, 130, 170)
COAL = (25, 25, 25)
CARROT = (255, 120, 0)
STICK = (140, 90, 40)
HAT = (90, 60, 160)
GREEN = (60, 170, 60)
YELLOW = (255, 200, 0)


def season(month):
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"


def blob(b, cx, y, widths, c):
    """Rows of the given widths, centred on cx: a cheap way to draw round things."""
    for i, w in enumerate(widths):
        b.rect(cx - w // 2, y + i, w, 1, c)


def hop(f, period, height):
    """Height above the ground for a bouncing thing, 0 .. height."""
    u = (f % period) / period
    return int(4 * height * u * (1 - u))


def sprite(b, x, y, rows, pal, flip=False, scale=1):
    """Draw a little picture: rows of characters, each looked up in `pal` ('.' and spaces are see-through).
    Runs of the same colour are drawn as one rectangle, so it stays cheap. scale=2 makes it twice as big."""
    for j, row in enumerate(rows):
        n = len(row)
        i = 0
        while i < n:
            ch = row[n - 1 - i] if flip else row[i]
            k = i + 1
            while k < n and (row[n - 1 - k] if flip else row[k]) == ch:
                k += 1
            col = pal.get(ch)
            if col is not None:
                b.rect(x + i * scale, y + j * scale, (k - i) * scale, scale, col)
            i = k


class Cameo:
    total = 200
    months = None     # restrict to these months (1-12); None = the whole season
    dates = None      # holiday cameos: (month, first day, last day)
    day = True        # daytime scene: gets a sky colour behind it when it's light out

    def __init__(self):
        self.frame = 0

    @property
    def done(self):
        return self.frame >= self.total

    def draw(self, b, sky=None):
        b.clear()
        if sky and self.day:
            b.rect(0, 0, b.w, b.h, sky)
        self.render(b, self.frame)
        self.frame += 1


# -- winter ----------------------------------------------------------------
def snowfall(b, f):
    for k in range(14):
        x = (k * 19 + 7) % 64 + ((f // 9 + k) % 3) - 1
        b.rect(x, (f // 2 + k * 11) % 32, 1, 1, FLAKE)


def snow_ground(b):
    b.rect(0, 30, 64, 2, dim(SNOW, 0.35))


def snow_head(b, cx, top, facing=1, dazed=False):
    b.rect(cx - 3, top - 1, 7, 1, HAT)
    b.rect(cx - 2, top - 4, 5, 3, HAT)
    blob(b, cx, top, (3, 5, 5, 5, 3), SNOW)
    b.rect(cx - 2, top + 1, 1, 1, COAL)
    b.rect(cx + 1, top + 1, 1, 1, COAL)
    if dazed:
        b.rect(cx - 1, top + 3, 3, 1, COAL)
    else:
        b.rect(cx + facing * 2, top + 2, 2, 1, CARROT)


def snow_body(b, cx, lift, arms_up=False, swing=0):
    base = 30 - lift
    blob(b, cx, base - 7, (5, 7, 9, 9, 9, 7, 5), SNOW)
    blob(b, cx, base - 12, (3, 5, 7, 7, 5), SNOW)
    b.rect(cx, base - 11, 1, 1, COAL)
    b.rect(cx, base - 9, 1, 1, COAL)
    if arms_up:
        for s in (-1, 1):
            b.rect(cx + s * 5 - (s < 0), base - 12, 1, 3, STICK)
            b.rect(cx + s * 4 - (s < 0), base - 13 + swing, 1, 1, STICK)
    else:
        b.rect(cx - 6, base - 11 + swing, 3, 1, STICK)
        b.rect(cx + 4, base - 11 - swing, 3, 1, STICK)
    return base - 17    # where a head sits


class SnowmanWalk(Cameo):
    total = 210

    def render(self, b, f):
        snowfall(b, f)
        snow_ground(b)
        cx = -8 + (f * 2) // 5
        lift = (f // 5) % 2
        top = snow_body(b, cx, lift, swing=lift)
        snow_head(b, cx, top)


class SnowmanOops(Cameo):
    total = 230

    def __init__(self):
        Cameo.__init__(self)
        self.hx = self.hy = self.vx = self.vy = 0.0

    def render(self, b, f):
        snowfall(b, f)
        snow_ground(b)
        cx = 28
        if f < 50:
            cx = -8 + (f * 36) // 50
        wobble = 0
        if 60 <= f < 85:
            wobble = (1 if (f // 2) % 2 else -1) if f > 72 else (f // 3) % 2
        lift = (f // 5) % 2 if f < 50 else 0
        flail = f >= 85
        top = snow_body(b, cx, lift, arms_up=flail, swing=(f // 3) % 2 if flail else 0)
        if f < 85:
            snow_head(b, cx + wobble, top)
            self.hx, self.hy, self.vx, self.vy = cx, top, 0.6, 0.0
        else:
            # head is on its own now: falls, bounces, rolls away
            self.vy += 0.2
            self.hy += self.vy
            self.hx += self.vx
            if self.hy >= 25:
                self.hy = 25
                self.vy = -self.vy * 0.45
                if abs(self.vy) < 0.7:
                    self.vy = 0
                    self.vx *= 0.96
            snow_head(b, int(self.hx), int(self.hy), dazed=True)
        if f >= 120:
            s = "OOPS!"
            b.text((b.w - text_width(s)) // 2, 3, s, AMBER)


# -- spring ----------------------------------------------------------------
class Sprouts(Cameo):
    total = 250
    XS = (6, 17, 27, 38, 48, 58)
    MAXH = (9, 12, 8, 13, 10, 11)
    BLOOM = ((255, 110, 180), YELLOW, (110, 150, 255), (255, 70, 70), WHITE, (190, 110, 255))

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (30, 90, 30))
        cloud = -8 + (f * 9) // 20
        if cloud < 72:
            blob(b, cloud, 2, (5, 9, 11, 9), (150, 160, 190))
            for k in range(3):
                b.rect(cloud - 3 + k * 3, 7 + (f * 2 + k * 5) % 14, 1, 2, (90, 150, 255))
        for i, x in enumerate(self.XS):
            t = f - (x + 8) * 20 // 9
            if t < 0:
                continue
            h = min(self.MAXH[i], t // 3 + 1)
            b.rect(x, 30 - h, 1, h, GREEN)
            if h >= 5:
                b.rect(x - 2, 30 - h // 2 - 1, 2, 1, GREEN)
                b.rect(x + 1, 30 - h // 2, 2, 1, GREEN)
            if h < self.MAXH[i]:
                continue
            stage = (t // 3 - self.MAXH[i]) // 7
            c = self.BLOOM[i]
            ty = 30 - h
            if stage <= 0:
                b.rect(x, ty - 1, 1, 1, c)
            else:
                b.rect(x - 1, ty - 1, 3, 1, c)
                b.rect(x, ty - 2, 1, 3, c)
                if stage >= 2:
                    b.rect(x, ty - 1, 1, 1, YELLOW if c != YELLOW else CARROT)


# -- summer ----------------------------------------------------------------
class SunShades(Cameo):
    total = 220
    RAYS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))

    def render(self, b, f):
        cx = 32
        rise = max(0, 32 - f) if f < 32 else (max(0, f - 185) * 2 if f > 185 else 0)
        top = 9 + rise
        for i, (dx, dy) in enumerate(self.RAYS):
            lit = (i + f // 6) % 2 == 0
            r = 8 + (f // 5) % 2
            b.rect(cx + dx * r - 1, top + 5 + dy * r - 1, 2, 2, YELLOW if lit else dim(YELLOW, 0.4))
        blob(b, cx, top, (5, 7, 9, 11, 11, 11, 11, 11, 9, 7, 5), YELLOW)
        face = (150, 80, 0)
        if f < 70:
            b.rect(cx - 3, top + 4, 1, 2, face)
            b.rect(cx + 3, top + 4, 1, 2, face)
        if f >= 70:
            # shades drop in from the top and settle with a little bounce
            sy = min(top + 3, -4 + (f - 70) * 2)
            if f > 90:
                sy = top + 3 - (1 if f < 94 else 0)
            b.rect(cx - 5, sy, 4, 3, COAL)
            b.rect(cx + 2, sy, 4, 3, COAL)
            b.rect(cx - 1, sy, 3, 1, COAL)
            if f > 95 and (f // 6) % 8 == 0:
                b.rect(cx - 4, sy, 1, 1, WHITE)
        b.rect(cx - 2, top + 8, 5, 1, face)
        b.rect(cx - 3, top + 7, 1, 1, face)
        b.rect(cx + 3, top + 7, 1, 1, face)


# -- fall ------------------------------------------------------------------
class Pumpkin(Cameo):
    day = False
    total = 230

    def render(self, b, f):
        if f < 60:
            cx = -8 + (f * 40) // 60
        elif f < 150:
            cx = 32
        else:
            cx = 32 + ((f - 150) * 40) // 60
        moving = f < 60 or f >= 150
        top = 19 - (hop(f, 20, 7) if moving else 0)
        blob(b, cx, top, (7, 11, 13, 15, 15, 15, 15, 15, 13, 11, 7), (255, 120, 0))
        for dx in (-4, 0, 4):
            b.rect(cx + dx, top + 1, 1, 9, (200, 90, 0))
        b.rect(cx - 1, top - 2, 2, 2, GREEN)
        b.rect(cx + 1, top - 3, 1, 1, GREEN)
        glow = (255, 225, 70) if (f // 3 + f // 7) % 4 else (200, 140, 20)
        for ex in (cx - 5, cx + 2):       # triangle eyes
            b.rect(ex + 1, top + 3, 1, 1, glow)
            b.rect(ex, top + 4, 3, 1, glow)
        b.rect(cx - 5, top + 7, 11, 1, glow)  # jagged grin
        b.rect(cx - 4, top + 8, 2, 1, glow)
        b.rect(cx - 1, top + 8, 2, 1, glow)
        b.rect(cx + 2, top + 8, 2, 1, glow)
        if 95 <= f < 140:
            b.text((b.w - text_width("BOO!")) // 2, 3, "BOO!", AMBER)


# -- more winter -------------------------------------------------------------
PENGUIN = (50, 60, 110)


class PenguinSlide(Cameo):
    """Waddles in, then flops onto its belly and toboggans off."""
    total = 105

    def render(self, b, f):
        snowfall(b, f)
        snow_ground(b)
        if f < 45:
            x = -6 + (f * 3) // 5
            top = 21 + (f // 4) % 2
            blob(b, x, top, (3, 5, 5, 5, 5, 5, 3), PENGUIN)
            b.rect(x - 1, top + 2, 3, 4, SNOW)
            b.rect(x + 1, top + 1, 1, 1, WHITE)
            b.rect(x + 2, top + 2, 2, 1, CARROT)
            b.rect(x - 3, top + 3, 1, 3, PENGUIN)
            b.rect(x - 2 + (f // 4) % 2 * 2, 28, 2, 1, CARROT)
            b.rect(x + 1 - (f // 4) % 2 * 2, 28, 2, 1, CARROT)
        else:
            x = 21 + (f - 45) * 3 // 2
            b.rect(x, 26, 10, 3, PENGUIN)
            b.rect(x + 1, 25, 8, 1, PENGUIN)
            b.rect(x + 1, 28, 8, 1, SNOW)
            b.rect(x + 8, 24, 3, 3, PENGUIN)
            b.rect(x + 9, 25, 1, 1, WHITE)
            b.rect(x + 11, 26, 2, 1, CARROT)
            b.rect(x - 2, 26 + (f // 3) % 2, 2, 1, CARROT)
            for k in range(1, 5):
                b.rect(x - 2 - k * 3, 28 - k % 2, 1, 1, dim(SNOW, 0.9 - 0.2 * k))


# -- more spring -------------------------------------------------------------
class Butterfly(Cameo):
    """A butterfly flutters in, loops over the flower, then flutters off."""
    total = 170

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (30, 90, 30))
        for x, h, c in ((12, 6, YELLOW), (52, 8, (110, 150, 255))):
            b.rect(x, 30 - h, 1, h, GREEN)
            b.rect(x - 1, 29 - h, 3, 1, c)
            b.rect(x, 28 - h, 1, 3, c)
        b.rect(32, 17, 1, 13, GREEN)
        b.rect(29, 24, 3, 1, GREEN)
        b.rect(33, 22, 3, 1, GREEN)
        pink = (255, 110, 180)
        b.rect(29, 16, 7, 3, pink)
        b.rect(31, 14, 3, 7, pink)
        b.rect(31, 16, 3, 3, YELLOW)
        if f < 60:
            x = -6 + f * 38 // 60
        elif f < 123:
            x = 32 + int(7 * math.sin((f - 60) / 10))
        else:
            x = 32 + (f - 123) * 4 // 5
        y = 8 + int(3 * math.sin(f / 5))
        if f >= 123:
            y -= (f - 123) // 8
        b.rect(x, y - 1, 1, 3, (60, 30, 10))
        if (f // 3) % 2:
            for wx in (x - 3, x + 1):
                b.rect(wx, y - 1, 3, 3, (255, 140, 20))
            b.rect(x - 2, y, 1, 1, WHITE)
            b.rect(x + 2, y, 1, 1, WHITE)
        else:
            b.rect(x - 1, y - 1, 1, 2, (255, 140, 20))
            b.rect(x + 1, y - 1, 1, 2, (255, 140, 20))


# -- more summer -------------------------------------------------------------
class IceCream(Cameo):
    """A scoop sweats, slides off the cone and splats."""
    total = 190

    def render(self, b, f):
        blob(b, 58, 4, (3, 5, 5, 5, 3), YELLOW)
        cx = 32
        pink = (255, 140, 190)
        b.rect(cx - 1, 25, 3, 6, (240, 190, 150))
        blob(b, cx, 17, (9, 7, 7, 5, 5, 3, 3, 1), (230, 170, 90))
        dx = dy = 0
        if f > 70:
            t = f - 70
            dx = t * 3 // 10
            dy = t * t // 25
        sy = min(12 + dy, 26)
        if f < 100 or sy < 26:
            blob(b, cx + dx, sy, (5, 7, 9, 9), pink)
            b.rect(cx + dx, sy - 1, 2, 2, RED_CHERRY)
            if 30 <= f < 70:
                b.rect(cx + 4, 15 + (f - 30) % 12, 1, 2, pink)
        else:
            blob(b, cx + dx, 28, (11, 13), pink)
            b.rect(cx + dx, 26, 2, 2, RED_CHERRY)
            b.text((b.w - text_width("OH NO!")) // 2, 3, "OH NO!", AMBER)


RED_CHERRY = (230, 20, 40)


class Fireflies(Cameo):
    day = False
    total = 220

    def render(self, b, f):
        blob(b, 56, 4, (3, 5, 5, 5, 3), (255, 240, 170))
        blob(b, 58, 4, (2, 3, 3, 3, 2), (0, 0, 0))
        for x in range(0, 64, 3):
            b.rect(x, 29 - (x * 7) % 3, 1, 3, (10, 40, 10))
        b.rect(0, 31, 64, 1, (10, 40, 10))
        for k in range(10):
            x = (k * 13 + 5) % 60 + int(4 * math.sin(f / 17 + k * 1.7))
            y = 8 + (k * 7) % 18 + int(3 * math.cos(f / 21 + k))
            lit = math.sin(f / 6 + k * 2.1)
            if lit <= 0:
                continue
            c = (190, 255, 60)
            b.rect(x, y, 1, 1, dim(c, lit))
            for gx, gy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                b.rect(x + gx, y + gy, 1, 1, dim(c, lit * 0.2))


class BeachBall(Cameo):
    total = 170
    STRIPES = ((230, 40, 40), WHITE, (60, 120, 255))

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (190, 160, 80))
        x = -8 + f * 47 // 100
        h = hop(f, 24, 14)
        top = 21 - h
        b.rect(x - 3 + h // 3, 30, 7 - h // 3 * 2, 1, (120, 100, 50))
        rot = f * 4 // 5
        for i, w in enumerate((3, 7, 9, 9, 9, 9, 9, 7, 3)):
            for px in range(x - w // 2, x - w // 2 + w):
                b.rect(px, top + i, 1, 1, self.STRIPES[((px - x + rot) // 3) % 3])


# -- more fall ---------------------------------------------------------------
class Leaves(Cameo):
    months = (9, 10, 11)
    total = 220
    COLORS = ((255, 120, 0), (220, 40, 20), (255, 200, 0), (170, 90, 20))

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (60, 40, 20))
        for k in range(12):
            y = (f * (3 + k % 3) // 8 + k * 9) % 36 - 4
            x = (k * 37) % 62 + int(3 * math.sin(f / 12 + k))
            c = self.COLORS[k % 4]
            b.rect(x, y, 2, 2, c)
            b.rect(x + 1, y - 1, 1, 1, dim(c, 0.6))
        for i, w in enumerate((24, 17, 11, 6, 2)[:min(5, f // 35)]):
            b.rect(32 - w // 2, 29 - i, w, 1, self.COLORS[(i + 3) % 4] if i % 2 else self.COLORS[3])


class GhostBat(Cameo):
    day = False
    months = (10,)
    total = 230

    def render(self, b, f):
        blob(b, 54, 5, (3, 5, 5, 5, 3), (255, 240, 170))
        gx = -6 + f * 76 // 230
        gy = 12 + int(3 * math.sin(f / 9))
        if (f // 9) % 5:
            c = (230, 230, 250)
            blob(b, gx, gy, (5, 7, 9, 9, 9, 9, 9, 9, 9), c)
            for i in range(-4, 5):
                if (i + f // 5) % 3:
                    b.rect(gx + i, gy + 9, 1, 2, c)
            b.rect(gx - 2, gy + 3, 1, 2, COAL)
            b.rect(gx + 1, gy + 3, 1, 2, COAL)
            b.rect(gx, gy + 6, 1, 2, COAL)
        if 60 <= f < 150:
            x = 70 - (f - 60) * 80 // 90
            y = 6 + int(2 * math.sin(f / 4))
            c = (170, 110, 220)
            b.rect(x, y, 2, 2, c)
            b.rect(x, y - 1, 1, 1, c)
            b.rect(x + 1, y - 1, 1, 1, c)
            if (f // 3) % 2:
                b.rect(x - 3, y - 2, 3, 1, c)
                b.rect(x + 2, y - 2, 3, 1, c)
                b.rect(x - 1, y - 1, 1, 1, c)
            else:
                b.rect(x - 3, y + 1, 3, 1, c)
                b.rect(x + 2, y + 1, 3, 1, c)
                b.rect(x - 1, y, 1, 1, c)


class Turkey(Cameo):
    months = (11,)
    total = 240
    FAN = ((200, 40, 20), (255, 140, 0), (255, 200, 0), (150, 90, 30))

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (60, 40, 20))
        if f < 70:
            cx = -10 + f * 42 // 70
        elif f < 165:
            cx = 32
        else:
            cx = 32 + (f - 165) * 46 // 75
        walking = f < 70 or f >= 165
        r = 5
        if 70 <= f < 95:
            r = 5 + (f - 70) * 6 // 25
        elif 95 <= f < 150:
            r = 11 + (f // 3) % 2
        elif 150 <= f < 165:
            r = 11 - (f - 150) * 6 // 15
        lift = (f // 5) % 2 if walking else 0
        by = 22 - lift
        for dx in range(-r, 3):
            for dy in range(-r, 1):
                d = int(math.sqrt(dx * dx + dy * dy))
                if 2 <= d <= r and (dx + dy) % 4:
                    b.rect(cx - 2 + dx, by + dy, 1, 1, self.FAN[(d // 2) % 4])
        blob(b, cx, by - 3, (5, 7, 9, 9, 7, 5), (120, 70, 30))
        b.rect(cx - 2, by + 3, 1, 4 + lift, (230, 150, 30))
        b.rect(cx + 1, by + 3, 1, 4 + lift, (230, 150, 30))
        b.rect(cx + 3, by - 7, 2, 4, (120, 70, 30))
        b.rect(cx + 4, by - 9, 3, 3, (120, 70, 30))
        b.rect(cx + 7, by - 8, 2, 1, (230, 150, 30))
        b.rect(cx + 6, by - 7, 1, 2, (220, 20, 20))
        b.rect(cx + 5, by - 9, 1, 1, WHITE)
        if 100 <= f < 150:
            b.text((b.w - text_width("GOBBLE")) // 2, 3, "GOBBLE", AMBER)


# -- holidays (on their own dates) -------------------------------------------
class Fireworks(Cameo):
    dates = (7, 3, 5)
    day = False
    total = 200
    COLORS = ((255, 60, 60), (255, 200, 0), (90, 150, 255), (90, 230, 120), (255, 110, 200), WHITE)
    SHOTS = ((14, 18, 9), (60, 40, 14), (110, 20, 8), (150, 46, 12))  # (start, x, burst height)

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (20, 20, 30))
        for n, (t0, x, top) in enumerate(self.SHOTS):
            t = f - t0
            if t < 0:
                continue
            if t < 22:
                y = 30 - t * (30 - top) // 22
                b.rect(x, y, 1, 1, WHITE)
                b.rect(x, y + 2, 1, 1, dim(AMBER, 0.5))
                continue
            age = t - 22
            if age > 36:
                continue
            c = self.COLORS[(n * 2 + t0) % 6]
            fade = 1.0 - age / 36
            r = 1 + age * 0.35
            for k in range(20):
                a = k * math.pi / 10
                px = x + int(r * math.cos(a))
                py = top + int(r * math.sin(a) * 0.9 + age * age * 0.006)
                b.rect(px, py, 1, 1, dim(c, fade))
                if age > 6:
                    b.rect(int(x + (r - 3) * math.cos(a)), int(top + (r - 3) * math.sin(a) * 0.9), 1, 1,
                           dim(c, fade * 0.4))


class XmasTree(Cameo):
    dates = (12, 14, 26)
    day = False
    total = 210
    LIGHTS = ((255, 60, 60), (255, 200, 0), (90, 150, 255), (255, 110, 200))

    def render(self, b, f):
        snowfall(b, f)
        snow_ground(b)
        cx = 32
        widths = (1, 3, 5, 3, 5, 7, 9, 5, 7, 9, 11, 13, 7, 9, 11, 13, 15, 17, 19)
        top = 7
        for i, w in enumerate(widths):
            b.rect(cx - w // 2, top + i, w, 1, (20, 120, 40) if i % 3 else (30, 150, 55))
            if i % 2 == 1 and w > 3 and (f // 7 + i) % 3:
                lx = cx - w // 2 + 1 + (i * 5) % (w - 2)
                b.rect(lx, top + i, 1, 1, self.LIGHTS[(i + f // 9) % 4])
        b.rect(cx - 1, top + len(widths), 3, 3, (110, 70, 30))
        star = YELLOW if (f // 5) % 3 else WHITE
        b.rect(cx - 1, top - 2, 3, 1, star)
        b.rect(cx, top - 3, 1, 3, star)
        for gx, c in ((cx - 18, (220, 40, 40)), (cx + 13, (60, 120, 255))):
            b.rect(gx, 26, 5, 4, c)
            b.rect(gx + 2, 26, 1, 4, YELLOW)
            b.rect(gx, 27, 5, 1, YELLOW)


class Heart(Cameo):
    dates = (2, 13, 14)
    day = False
    total = 190
    ROWS = ("00111011100", "01111111110", "11111111111", "11111111111", "01111111110",
            "00111111100", "00011111000", "00001110000", "00000100000")

    def render(self, b, f):
        for k in range(6):  # little hearts drifting up
            y = 31 - (f * (1 + k % 2) // 2 + k * 11) % 40
            x = (k * 21 + 6) % 60
            c = dim((255, 90, 150), 0.5)
            b.rect(x, y, 1, 1, c)
            b.rect(x + 2, y, 1, 1, c)
            b.rect(x, y + 1, 3, 1, c)
            b.rect(x + 1, y + 2, 1, 1, c)
        beat = 0.75 + 0.25 * math.sin(f / 4.0)
        c = dim((255, 40, 90), beat)
        ox, oy = 26, 10 - (1 if (f // 8) % 2 else 0)
        for j, row in enumerate(self.ROWS):
            for i, ch in enumerate(row):
                if ch == "1":
                    b.rect(ox + i, oy + j, 1, 1, c)
        b.rect(ox + 2, oy + 1, 2, 1, WHITE)
        b.rect(ox + 2, oy + 2, 1, 1, WHITE)


class Shamrock(Cameo):
    dates = (3, 16, 17)
    total = 170

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (20, 80, 30))
        cx = 32
        cy = min(14, -8 + f // 2 * 2) if f < 40 else 14 - hop(f - 40, 30, 4)
        g = (30, 200, 60)
        for dx, dy in ((-3, -3), (2, -3), (-3, 2), (2, 2)):
            blob(b, cx + dx + 1, cy + dy, (2, 4, 4, 2), g)
        b.rect(cx, cy + 1, 1, 1, dim(g, 0.5))
        b.rect(cx, cy + 5, 1, 30 - cy - 5, (20, 140, 40))
        if f > 40:
            for k in range(8):
                a = f / 9 + k * 0.8
                b.rect(cx + int(11 * math.cos(a)), cy + int(8 * math.sin(a * 1.3)), 1, 1,
                       YELLOW if (f // 3 + k) % 2 else WHITE)
            b.text((b.w - text_width("LUCKY!")) // 2, 3, "LUCKY!", AMBER)


# -- our teams ---------------------------------------------------------------
SEA_GREEN = (105, 220, 40)
SEA_NAVY = (20, 60, 130)
GREY_HAWK = (165, 172, 180)


class HawkFly(Cameo):
    total = 115

    def render(self, b, f):
        x = -10 + f * 7 // 8
        y = 11 + int(3 * math.sin(f / 9))
        b.rect(x - 3, y, 3, 1, SEA_NAVY)
        b.rect(x, y, 5, 2, GREY_HAWK)
        b.rect(x + 5, y - 1, 2, 2, GREY_HAWK)
        b.rect(x + 7, y, 1, 1, YELLOW)
        b.rect(x + 6, y - 1, 1, 1, COAL)
        if (f // 4) % 2:
            b.rect(x + 1, y - 4, 2, 4, SEA_GREEN)
            b.rect(x, y - 5, 1, 2, SEA_GREEN)
        else:
            b.rect(x + 1, y + 2, 2, 3, SEA_GREEN)
            b.rect(x, y + 4, 1, 2, SEA_GREEN)
        if 20 < f < 100:
            b.text((b.w - text_width("GO HAWKS!")) // 2, 24, "GO HAWKS!", SEA_GREEN)


class Flag12(Cameo):
    total = 160

    def render(self, b, f):
        b.rect(10, 4, 1, 27, GREY_HAWK)
        b.rect(9, 3, 3, 1, YELLOW)
        fy = max(5, 31 - f * 26 // 60) if f < 60 else 5
        sway = int(math.sin(f / 5) * 1.2)
        b.rect(11, fy, 20, 13, SEA_NAVY)
        b.rect(11, fy, 20, 1, SEA_GREEN)
        b.rect(11, fy + 12, 20, 1, SEA_GREEN)
        b.text(15 + sway, fy + 2, "12", SEA_GREEN, 2)
        if f > 60:
            b.text(36, 9, "GO", WHITE)
            b.text(36, 16, "HAWKS", SEA_GREEN if (f // 6) % 2 else WHITE)


class KrakenTentacle(Cameo):
    day = False
    total = 170
    TEAL = (70, 210, 230)

    def render(self, b, f):
        b.rect(0, 28, 64, 4, (0, 30, 70))
        grow = min(1.0, f / 40) if f < 130 else max(0.0, (170 - f) / 40)
        for t, x0 in enumerate((8, 22, 44, 56)):
            n = int((14 + (t % 2) * 4) * grow)
            for j in range(n):
                x = x0 + int((2 + j * 0.25) * math.sin(f / 7 - j * 0.45 + t * 1.5))
                b.rect(x, 29 - j, 2, 1, self.TEAL)
                if j % 3 == 1:
                    b.rect(x + 2, 29 - j, 1, 1, dim(self.TEAL, 0.5))
        if 60 < f < 150:
            rise = min(1.0, (f - 60) / 20) if f < 130 else max(0.0, (150 - f) / 20)
            ey = 31 - int(11 * rise)
            blob(b, 33, ey, (7, 9, 9, 9, 7), WHITE)
            px = 33 + int(2 * math.sin(f / 8))
            b.rect(px - 1, ey + 1, 3, 3, COAL)
            b.rect(px, ey + 2, 1, 1, self.TEAL)


class DodgerBall(Cameo):
    total = 150
    BLUE = (0, 110, 255)

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (60, 40, 20))
        x = -6 + f * 76 // 150
        h = hop(f, 30, 12)
        top = 22 - h
        blob(b, x, top, (5, 7, 7, 7, 7, 7, 5), WHITE)
        rot = f // 3 % 4
        for j in range(1, 6, 2):
            b.rect(x - 2 + (rot + j) % 3, top + j, 1, 1, (220, 30, 30))
            b.rect(x + 2 - (rot + j) % 3, top + j, 1, 1, (220, 30, 30))
        if f > 10:
            b.text((b.w - text_width("GO DODGERS")) // 2, 3, "GO DODGERS", self.BLUE if (f // 8) % 2 else WHITE)


# -- scoring celebrations: full-panel, played when one of our teams scores ------
def pts_label(n, unit):
    return "+%d" % n if unit == "pts" else ("+%d" % n)


class HawkScore(Cameo):
    """A seahawk swoops across: GO HAWKS and the points just scored."""
    total = 120

    def __init__(self, points=7, unit="pts"):
        Cameo.__init__(self)
        self.label = pts_label(points, unit)

    def render(self, b, f):
        x = -10 + f * 80 // 100
        y = 9 + int(4 * math.sin(f / 8))
        b.rect(x - 4, y + 1, 4, 1, SEA_GREEN)
        b.rect(x - 8, y + 1, 3, 1, SEA_NAVY)
        b.rect(x, y, 6, 3, GREY_HAWK)
        b.rect(x + 6, y - 1, 3, 3, GREY_HAWK)
        b.rect(x + 9, y, 2, 1, YELLOW)
        b.rect(x + 7, y - 1, 1, 1, COAL)
        if (f // 4) % 2:
            b.rect(x + 1, y - 5, 3, 5, SEA_GREEN)
            b.rect(x, y - 6, 1, 2, SEA_GREEN)
        else:
            b.rect(x + 1, y + 3, 3, 4, SEA_GREEN)
            b.rect(x, y + 6, 1, 2, SEA_GREEN)
        if f > 12:
            b.text((b.w - text_width("GO HAWKS!")) // 2, 21, "GO HAWKS!", SEA_GREEN if (f // 5) % 2 else WHITE)
        if f > 25:
            b.text((b.w - text_width(self.label)) // 2, 27, self.label, YELLOW if (f // 4) % 2 else WHITE)


class KrakenScore(Cameo):
    """A kraken bursts out of the water with GOAL! on its back."""
    day = False
    total = 130
    TEAL = (70, 210, 230)

    def render(self, b, f):
        for y in range(24, 32):
            b.rect(0, y, 64, 1, (0, 20 + (y - 24) * 4, 60 + (y - 24) * 6))
        rise = min(1.0, f / 25) if f < 95 else max(0.0, (130 - f) / 35)
        top = 28 - int(22 * rise)
        blob(b, 32, top, (6, 10, 14, 16, 18, 18, 18), (150, 40, 70))
        b.rect(28, top + 2, 3, 3, WHITE)
        b.rect(34, top + 2, 3, 3, WHITE)
        b.rect(29, top + 3, 1, 2, COAL)
        b.rect(35, top + 3, 1, 2, COAL)
        for t, x0 in enumerate((14, 22, 42, 50)):
            n = int(16 * rise)
            for j in range(n):
                x = x0 + int((2 + j * 0.2) * math.sin(f / 6 - j * 0.5 + t))
                b.rect(x, 29 - j, 2, 1, self.TEAL)
        b.rect(0, 28, 64, 4, (0, 30, 80))
        if 15 < f < 110:
            b.text((b.w - text_width("GOAL!")) // 2, 1, "GOAL!", self.TEAL if (f // 5) % 2 else WHITE)


class DodgerScore(Cameo):
    """A baseball sails over the plate: RUN!"""
    total = 110
    BLUE = (0, 110, 255)

    def __init__(self, runs=1):
        Cameo.__init__(self)
        self.label = "RUN!" if runs == 1 else "%d RUNS!" % runs

    def render(self, b, f):
        b.rect(0, 30, 64, 2, (60, 40, 20))
        u = min(1.0, f / 70)
        x = int(-4 + 72 * u)
        y = int(26 - 24 * math.sin(u * math.pi))
        blob(b, x, y, (3, 5, 5, 5, 3), WHITE)
        b.rect(x - 1, y + 1, 1, 1, (220, 30, 30))
        b.rect(x + 1, y + 3, 1, 1, (220, 30, 30))
        if f > 5:
            b.text((b.w - text_width(self.label)) // 2, 12, self.label, self.BLUE if (f // 5) % 2 else WHITE)
        if f > 60:
            b.text((b.w - text_width("GO DODGERS")) // 2, 21, "GO DODGERS", WHITE)


def scoring(sport, n):
    """The celebration for one of our teams scoring n, or None for sports without one."""
    if sport == "football":
        return HawkScore(n)
    if sport == "hockey":
        return KrakenScore()
    if sport == "baseball":
        return DodgerScore(n)
    return None


CAMEOS = {
    "winter": (SnowmanWalk, SnowmanOops, PenguinSlide),
    "spring": (Sprouts, Butterfly),
    "summer": (SunShades, IceCream, Fireflies, BeachBall),
    "fall": (Pumpkin, Leaves, GhostBat, Turkey),
}
HOLIDAYS = (Fireworks, XmasTree, Heart, Shamrock)
TEAMS = (HawkFly, Flag12, KrakenTentacle, DodgerBall)
TEAM_OF = {HawkFly: ("football", "SEA"), Flag12: ("football", "SEA"),
           KrakenTentacle: ("hockey", "SEA"), DodgerBall: ("baseball", "LAD")}  # (sport, abbreviation) each one is about

# The extra cameos live in their own files and are only loaded while one plays, so they cost no memory
# the rest of the time. name -> (file, seasons or None for any, months or None, holiday dates or None).
# (test_critters checks this table against the files; make_extras_table.py rewrites it.)
EXTRAS = {
    'Invaders': ('extras_space', None, None, None),
    'Pacman': ('extras_space', None, None, None),
    'Robot': ('extras_space', None, None, None),
    'Rocket': ('extras_space', None, None, None),
    'Ufo': ('extras_space', None, None, None),
    'CatMouse': ('extras_fun', None, None, None),
    'Dino': ('extras_fun', None, None, None),
    'DogFetch': ('extras_fun', None, None, None),
    'Pizza': ('extras_fun', None, None, None),
    'Speaker': ('extras_fun', None, None, None),
    'FieldGoal': ('extras_sports', None, None, None),
    'HockeyGoal': ('extras_sports', None, None, None),
    'HomeRun': ('extras_sports', None, None, None),
    'Hoops': ('extras_sports', None, None, None),
    'Trophy': ('extras_sports', None, None, None),
    'HotCocoa': ('extras_winter', ('winter',), None, None),
    'IceSkater': ('extras_winter', ('winter',), None, None),
    'Sledding': ('extras_winter', ('winter',), None, None),
    'SnowAngel': ('extras_winter', ('winter',), None, None),
    'Fireplace': ('extras_winter2', ('winter',), None, None),
    'Icicles': ('extras_winter2', ('winter',), None, None),
    'NewYear': ('extras_winter2', ('winter',), None, (12, 30, 31)),
    'Reindeer': ('extras_winter2', ('winter',), (12,), None),
    'SnowballFight': ('extras_winter2', ('winter',), None, None),
    'Bee': ('extras_spring', ('spring',), None, None),
    'Bunny': ('extras_spring', ('spring',), (3, 4), None),
    'Chick': ('extras_spring', ('spring',), None, None),
    'FrogRain': ('extras_spring', ('spring',), None, None),
    'Kite': ('extras_spring', ('spring',), None, None),
    'Ladybug': ('extras_spring', ('spring',), None, None),
    'Rainbow': ('extras_spring', ('spring',), None, None),
    'Sailboat': ('extras_summer', ('summer',), None, None),
    'Sandcastle': ('extras_summer', ('summer',), None, None),
    'Seagull': ('extras_summer', ('summer',), None, None),
    'Surfer': ('extras_summer', ('summer',), None, None),
    'Watermelon': ('extras_summer', ('summer',), None, None),
    'Campfire': ('extras_summer2', ('summer',), None, None),
    'Crab': ('extras_summer2', ('summer',), None, None),
    'Lemonade': ('extras_summer2', ('summer',), None, None),
    'Palm': ('extras_summer2', ('summer',), None, None),
    'ShootingStar': ('extras_summer2', ('summer',), None, None),
    'AppleDrop': ('extras_fall', ('fall',), None, None),
    'Geese': ('extras_fall', ('fall',), None, None),
    'HarvestMoon': ('extras_fall', ('fall',), None, None),
    'Scarecrow': ('extras_fall', ('fall',), None, None),
    'Squirrel': ('extras_fall', ('fall',), None, None),
    'Cauldron': ('extras_fall2', ('fall',), (10,), None),
    'Mushrooms': ('extras_fall2', ('fall',), None, None),
    'Skeleton': ('extras_fall2', ('fall',), (10,), None),
    'Witch': ('extras_fall2', ('fall',), (10,), None),
}

_last = None
_loaded = []


def _make(choice, fallback):
    """The cameo for a pick: a class, or the name of an extra one to load from its file. If memory is short
    (or the file fails to load) one of the always-loaded cameos in `fallback` plays instead."""
    if isinstance(choice, str):
        import gc
        gc.collect()
        try:
            if gc.mem_free() < 90000:
                raise MemoryError
            module = EXTRAS[choice][0]
            cls = getattr(__import__(module), choice)
            if module not in _loaded:
                _loaded.append(module)
            return cls()
        except (MemoryError, ImportError):
            release()
            choice = random.choice(fallback)
    return choice()


def make(name):
    """A cameo by class name (for trying one from the settings page), or None."""
    if name in EXTRAS:
        return _make(name, [SnowmanWalk])
    for pool in list(CAMEOS.values()) + [HOLIDAYS, TEAMS]:
        for cls in pool:
            if cls.__name__ == name:
                return cls()
    return None


def release():
    """Unload the extra-cameo files (and free their memory); call when a cameo is over."""
    if _loaded:
        import sys
        for module in _loaded:
            sys.modules.pop(module, None)
        del _loaded[:]
        import gc
        gc.collect()


def pick(month, day=1, followed=None):
    """A random cameo: today's holiday 40% of the time, one of our teams one time in four.
    `followed` is the [(sport, abbreviation)] being followed: team cameos only appear for those teams."""
    global _last
    s = season(month)
    pool = [c for c in CAMEOS[s] if c.months is None or month in c.months]
    holiday = [c for c in HOLIDAYS if c.dates[0] == month and c.dates[1] <= day <= c.dates[2]]
    for name, (_, seasons, months, dates) in EXTRAS.items():
        if dates:
            if dates[0] == month and dates[1] <= day <= dates[2]:
                holiday.append(name)
        elif (seasons is None or s in seasons) and (months is None or month in months):
            pool.append(name)
    r = random.randint(0, 99)
    if holiday and r < 40:
        pool = holiday
    elif r >= 75:
        pool = [c for c in TEAMS if followed is None or TEAM_OF[c] in followed] or pool
    pool = [c for c in pool if c is not _last and c != _last] or pool
    _last = random.choice(pool)
    return _make(_last, [c for c in CAMEOS[s] if c.months is None or month in c.months])
