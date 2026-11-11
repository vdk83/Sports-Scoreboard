# Classic pixel-board light shows for the idle screen: Plasma, Matrix rain, Fire and a Warp starfield.
# Loaded only while one plays (see critters.EXTRAS).
import math

from board import dim
from critters import Cameo


class Lcg:
    def __init__(self, seed):
        self.s = seed

    def next(self, n):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.s >> 8) % n


class Plasma(Cameo):
    day = False
    total = 240
    BLOCK = 4

    def render(self, b, f):
        t = f * 0.08
        k = self.BLOCK
        for by in range(32 // k):
            for bx in range(64 // k):
                x, y = bx * 0.45, by * 0.45
                v = (math.sin(x + t) + math.sin(y * 1.3 - t * 0.7) + math.sin((x + y) * 0.7 + t * 0.5)
                     + math.sin(math.sqrt((x - 14) ** 2 + (y - 7) ** 2) * 0.6 - t)) / 4.0  # -1 .. 1
                p = (v + 1.0) / 2.0
                r = int(120 + 120 * math.sin(p * 6.283))
                g = int(120 + 120 * math.sin(p * 6.283 + 2.1))
                bl = int(120 + 120 * math.sin(p * 6.283 + 4.2))
                b.rect(bx * k, by * k, k, k, (max(0, r), max(0, g), max(0, bl)))


class MatrixRain(Cameo):
    day = False
    total = 260
    COLS = 32
    TRAIL = 9

    def __init__(self):
        Cameo.__init__(self)
        rng = Lcg(21)
        self.start = [rng.next(40) for _ in range(self.COLS)]
        self.speed = [1 + rng.next(3) for _ in range(self.COLS)]  # frames per row

    def render(self, b, f):
        for c in range(self.COLS):
            head = ((f // self.speed[c]) + self.start[c]) % (16 + self.TRAIL + 6) - self.TRAIL
            for i in range(self.TRAIL):
                y = head - i
                if 0 <= y < 16:
                    if i == 0:
                        col = (210, 255, 210)
                    else:
                        col = (0, max(40, 230 - i * 26), 20)
                    b.rect(c * 2, y * 2, 2, 2, col)


class Fire(Cameo):
    day = False
    total = 260
    W, H = 32, 16

    def __init__(self):
        Cameo.__init__(self)
        self.rng = Lcg(33)
        self.heat = [[0] * self.W for _ in range(self.H)]
        self.last = 0

    def step(self):
        w, h, a = self.W, self.H, self.heat
        for x in range(w):
            a[h - 1][x] = 200 + self.rng.next(56) if self.rng.next(5) else 60
        for y in range(h - 1):
            row, below = a[y], a[y + 1]
            for x in range(w):
                s = below[x] * 2 + below[(x - 1) % w] + below[(x + 1) % w]
                row[x] = max(0, s // 4 - self.rng.next(14))

    @staticmethod
    def color(v):
        if v < 60:
            return (v * 2, 0, 0)
        if v < 140:
            return (120 + (v - 60), (v - 60) * 2, 0)
        return (255, min(255, 160 + (v - 140)), min(255, (v - 140) * 2))

    def render(self, b, f):
        if f < self.last:
            self.__init__()
        while self.last <= f:
            self.step()
            self.last += 1
        for y in range(self.H):
            row = self.heat[y]
            for x in range(self.W):
                v = row[x]
                if v > 25:
                    b.rect(x * 2, y * 2, 2, 2, self.color(v))


class Warp(Cameo):
    day = False
    total = 240
    STARS = 40

    def __init__(self):
        Cameo.__init__(self)
        rng = Lcg(2)
        self.ang = [rng.next(628) / 100.0 for _ in range(self.STARS)]
        self.off = [rng.next(60) for _ in range(self.STARS)]

    def render(self, b, f):
        speed = 0.6 + min(f, 120) / 120.0 * 1.4  # speeds up as it goes
        for i in range(self.STARS):
            d = ((f * speed + self.off[i]) % 60) / 60.0  # 0 (centre) .. 1 (edge)
            r = d * d * 40
            x = 32 + math.cos(self.ang[i]) * r * 1.6
            y = 16 + math.sin(self.ang[i]) * r
            if 0 <= x < 64 and 0 <= y < 32:
                v = 0.25 + d * 0.75
                b.rect(int(x), int(y), 1, 1, dim((255, 255, 255), v))
                if d > 0.6:  # a streak behind fast stars
                    b.rect(int(32 + math.cos(self.ang[i]) * (r - 2) * 1.6), int(16 + math.sin(self.ang[i]) * (r - 2)), 1, 1,
                           dim((150, 180, 255), v * 0.6))
