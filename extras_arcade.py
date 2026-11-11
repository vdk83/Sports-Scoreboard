# Arcade-style idle cameos: Tetris, Asteroids and spinning cubes. Loaded only while one plays (see critters.EXTRAS).
# Written from scratch for this board; the idea of vector/arcade scenes came from the pixel-art clock projects.
import math

from board import AMBER, WHITE, dim
from critters import Cameo

CYAN = (60, 220, 255)
GREY = (150, 150, 160)
RED = (230, 40, 40)


def line(b, x0, y0, x1, y1, c):
    """A one-pixel line (the board clips anything off the panel)."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    for _ in range(200):
        b.rect(x0, y0, 1, 1, c)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def rainbow(t):
    """Colour wheel: t in turns (0-1 repeating) -> (r, g, b)."""
    t = (t % 1.0) * 3
    k = int(t)
    f = int((t - k) * 255)
    return ((255 - f, f, 0), (0, 255 - f, f), (f, 0, 255 - f))[k]


class Lcg:
    """A tiny repeatable random generator, so a cameo plays the same way every time."""

    def __init__(self, seed):
        self.s = seed

    def next(self, n):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.s >> 8) % n


class Tetris(Cameo):
    day = False
    total = 260
    W, H, CELL = 10, 15, 2
    SHAPES = (
        ((0, 0), (1, 0), (2, 0), (3, 0)),  # I
        ((0, 0), (1, 0), (0, 1), (1, 1)),  # O
        ((0, 0), (1, 0), (2, 0), (1, 1)),  # T
        ((1, 0), (2, 0), (0, 1), (1, 1)),  # S
        ((0, 0), (1, 0), (1, 1), (2, 1)),  # Z
        ((0, 0), (0, 1), (1, 1), (2, 1)),  # L
    )
    COLORS = ((60, 220, 255), (255, 220, 40), (190, 80, 255), (80, 220, 80), (240, 60, 60), (255, 150, 30))

    def __init__(self):
        Cameo.__init__(self)
        self.reset()
        self.last = 0

    def reset(self):
        self.grid = [[0] * self.W for _ in range(self.H)]
        self.rng = Lcg(7)
        self.lines = 0
        self.last = 0
        self.spawn()

    def fits(self, cells, x, y):
        for dx, dy in cells:
            cx, cy = x + dx, y + dy
            if cx < 0 or cx >= self.W or cy >= self.H or (cy >= 0 and self.grid[cy][cx]):
                return False
        return True

    def spawn(self):
        self.kind = self.rng.next(len(self.SHAPES))
        cells = self.SHAPES[self.kind]
        width = max(c[0] for c in cells) + 1
        best, best_y = 0, -1
        for x in range(self.W - width + 1):  # greedy: the column where it sinks lowest
            y = 0
            while self.fits(cells, x, y + 1):
                y += 1
            if y > best_y or (y == best_y and self.rng.next(2)):
                best, best_y = x, y
        self.target = best
        self.x = (self.W - width) // 2
        self.y = -1
        if not self.fits(cells, self.x, 0):
            self.grid = [[0] * self.W for _ in range(self.H)]  # topped out: start over

    def step(self):
        cells = self.SHAPES[self.kind]
        if self.x != self.target:
            nx = self.x + (1 if self.target > self.x else -1)
            if self.fits(cells, nx, self.y):
                self.x = nx
        if self.fits(cells, self.x, self.y + 1):
            self.y += 1
            return
        for dx, dy in cells:
            if 0 <= self.y + dy < self.H:
                self.grid[self.y + dy][self.x + dx] = self.kind + 1
        rows = [r for r in self.grid if not all(r)]
        gone = self.H - len(rows)
        if gone:
            self.lines += gone
            self.grid = [[0] * self.W for _ in range(gone)] + rows
        self.spawn()

    def render(self, b, f):
        if f < self.last:
            self.reset()
        while self.last < f:
            self.step()
            self.last += 1
        c = self.CELL
        x0, y0 = 22, 1
        b.rect(x0 - 1, y0 - 1, 1, self.H * c + 2, GREY)
        b.rect(x0 + self.W * c, y0 - 1, 1, self.H * c + 2, GREY)
        b.rect(x0 - 1, y0 + self.H * c, self.W * c + 2, 1, GREY)
        for r in range(self.H):
            for col in range(self.W):
                k = self.grid[r][col]
                if k:
                    b.rect(x0 + col * c, y0 + r * c, c, c, self.COLORS[k - 1])
        for dx, dy in self.SHAPES[self.kind]:
            if self.y + dy >= 0:
                b.rect(x0 + (self.x + dx) * c, y0 + (self.y + dy) * c, c, c, WHITE)
        b.text(1, 2, "LINES", GREY)
        s = str(self.lines)
        b.text(1, 9, s, AMBER)


class Asteroids(Cameo):
    day = False
    total = 300

    def __init__(self):
        Cameo.__init__(self)
        self.reset()

    def reset(self):
        self.rng = Lcg(3)
        self.last = 0
        self.angle = 0.0
        self.rocks = []   # [x, y, vx, vy, radius, shape seed]
        self.shots = []   # [x, y, vx, vy, life]
        self.cool = 0
        for _ in range(4):
            self.add_rock(self.rng.next(64), self.rng.next(2) * 31, 5)

    def add_rock(self, x, y, r):
        vx = (self.rng.next(9) - 4) / 8.0
        vy = (self.rng.next(9) - 4) / 8.0
        if vx == 0 and vy == 0:
            vx = 0.3
        self.rocks.append([float(x), float(y), vx, vy, r, self.rng.next(1000)])

    def step(self):
        for r in self.rocks:
            r[0] = (r[0] + r[2]) % 64
            r[1] = (r[1] + r[3]) % 32
        for s in self.shots:
            s[0] = (s[0] + s[2]) % 64
            s[1] = (s[1] + s[3]) % 32
            s[4] -= 1
        self.shots = [s for s in self.shots if s[4] > 0]
        if not self.rocks:
            for _ in range(4):
                self.add_rock(self.rng.next(64), self.rng.next(2) * 31, 5)
            return
        sx, sy = 32.0, 16.0  # the ship sits in the middle and turns to the nearest rock
        near = self.rocks[0]
        best = 9999.0
        for r in self.rocks:
            d = (r[0] - sx) ** 2 + (r[1] - sy) ** 2
            if d < best:
                best, near = d, r
        want = math.atan2(near[1] - sy, near[0] - sx)
        diff = (want - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.angle += max(-0.25, min(0.25, diff))
        self.cool -= 1
        if abs(diff) < 0.3 and self.cool <= 0:
            self.shots.append([sx, sy, math.cos(self.angle) * 2.5, math.sin(self.angle) * 2.5, 16])
            self.cool = 9
        for s in self.shots[:]:
            for r in self.rocks[:]:
                if (s[0] - r[0]) ** 2 + (s[1] - r[1]) ** 2 <= (r[4] + 1) ** 2:
                    self.rocks.remove(r)
                    self.shots.remove(s)
                    if r[4] > 2 and len(self.rocks) < 8:
                        self.add_rock(r[0], r[1], r[4] - 2)
                        self.add_rock(r[0], r[1], r[4] - 2)
                    break

    def render(self, b, f):
        if f < self.last:
            self.reset()
        while self.last < f:
            self.step()
            self.last += 1
        for r in self.rocks:
            n = 7
            pts = []
            for k in range(n):
                a = k * 2 * math.pi / n
                size = r[4] * (0.7 + ((r[5] * (k + 3)) % 7) / 15.0)
                pts.append((r[0] + math.cos(a) * size, r[1] + math.sin(a) * size))
            for k in range(n):
                p, q = pts[k], pts[(k + 1) % n]
                line(b, p[0], p[1], q[0], q[1], GREY)
        a = self.angle
        tip = (32 + math.cos(a) * 4, 16 + math.sin(a) * 4)
        left = (32 + math.cos(a + 2.5) * 3, 16 + math.sin(a + 2.5) * 3)
        right = (32 + math.cos(a - 2.5) * 3, 16 + math.sin(a - 2.5) * 3)
        line(b, tip[0], tip[1], left[0], left[1], CYAN)
        line(b, tip[0], tip[1], right[0], right[1], CYAN)
        line(b, left[0], left[1], right[0], right[1], dim(CYAN, 0.6))
        for s in self.shots:
            b.rect(int(s[0]), int(s[1]), 1, 1, (255, 230, 60))


class Cubes(Cameo):
    day = False
    total = 240
    VERTS = ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))
    EDGES = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))

    def cube(self, b, cx, cy, size, ax, ay, color):
        sa, ca = math.sin(ax), math.cos(ax)
        sb, cb = math.sin(ay), math.cos(ay)
        pts = []
        for x, y, z in self.VERTS:
            y, z = y * ca - z * sa, y * sa + z * ca
            x, z = x * cb + z * sb, -x * sb + z * cb
            k = size / (3.5 + z * 0.5)
            pts.append((cx + x * k * 1.6, cy + y * k * 1.6))
        for i, j in self.EDGES:
            line(b, pts[i][0], pts[i][1], pts[j][0], pts[j][1], color)

    def render(self, b, f):
        t = f / 60.0
        self.cube(b, 32, 16, 9, f * 0.05, f * 0.037, rainbow(t))
        self.cube(b, 12, 16, 5, -f * 0.07, f * 0.05, rainbow(t + 0.33))
        self.cube(b, 52, 16, 5, f * 0.06, -f * 0.045, rainbow(t + 0.66))
