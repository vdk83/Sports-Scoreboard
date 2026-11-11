# Self-playing mini games for the idle screen: Pong, Snake and Conway's Life. Loaded only while one plays
# (see critters.EXTRAS). Each plays out the same way every time (a small repeatable random generator).
from board import AMBER, WHITE, dim
from critters import Cameo

GREY = (150, 150, 160)
GREEN = (80, 230, 90)
RED = (230, 50, 50)


class Lcg:
    def __init__(self, seed):
        self.s = seed

    def next(self, n):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.s >> 8) % n


class Pong(Cameo):
    day = False
    total = 300
    PAD = 7

    def __init__(self):
        Cameo.__init__(self)
        self.reset()

    def reset(self):
        self.rng = Lcg(11)
        self.last = 0
        self.left = self.right = 12.0
        self.score = [0, 0]
        self.serve(1)

    def serve(self, d):
        self.bx, self.by = 32.0, float(8 + self.rng.next(16))
        self.vx = 1.1 * d
        self.vy = (self.rng.next(9) - 4) / 5.0 or 0.4

    def follow(self, y, target, speed):
        c = y + self.PAD / 2.0
        if target > c + 1:
            y += speed
        elif target < c - 1:
            y -= speed
        return max(0.0, min(32.0 - self.PAD, y))

    def step(self):
        self.bx += self.vx
        self.by += self.vy
        if self.by < 0 or self.by > 31:
            self.vy = -self.vy
            self.by = max(0.0, min(31.0, self.by))
        # the right paddle is a bit slower than the ball, so now and then it misses
        self.left = self.follow(self.left, self.by, 1.0)
        self.right = self.follow(self.right, self.by, 0.55)
        if self.vx < 0 and self.bx <= 3:
            if self.left - 1 <= self.by <= self.left + self.PAD:
                self.vx = -self.vx * 1.03
                self.vy += (self.by - (self.left + self.PAD / 2.0)) * 0.12
            else:
                self.score[1] += 1
                self.serve(1)
        elif self.vx > 0 and self.bx >= 60:
            if self.right - 1 <= self.by <= self.right + self.PAD:
                self.vx = -self.vx * 1.03
                self.vy += (self.by - (self.right + self.PAD / 2.0)) * 0.12
            else:
                self.score[0] += 1
                self.serve(-1)
        self.vx = max(-2.2, min(2.2, self.vx))
        self.vy = max(-1.6, min(1.6, self.vy))

    def render(self, b, f):
        if f < self.last:
            self.reset()
        while self.last < f:
            self.step()
            self.last += 1
        for y in range(0, 32, 4):
            b.rect(31, y, 1, 2, dim(GREY, 0.5))
        b.rect(1, int(self.left), 2, self.PAD, WHITE)
        b.rect(61, int(self.right), 2, self.PAD, WHITE)
        b.rect(int(self.bx), int(self.by), 2, 2, AMBER)
        b.text(22, 1, str(self.score[0]), GREY)
        b.text(38, 1, str(self.score[1]), GREY)


class Snake(Cameo):
    day = False
    total = 300
    W, H, CELL = 32, 16, 2

    def __init__(self):
        Cameo.__init__(self)
        self.reset()

    def reset(self):
        self.rng = Lcg(5)
        self.last = 0
        self.body = [(8, 8), (7, 8), (6, 8)]  # head first
        self.food = None
        self.place_food()
        self.flash = 0

    def place_food(self):
        for _ in range(60):
            p = (self.rng.next(self.W), self.rng.next(self.H))
            if p not in self.body:
                self.food = p
                return
        self.food = None

    def free(self, p):
        return 0 <= p[0] < self.W and 0 <= p[1] < self.H and p not in self.body[:-1]

    def step(self):
        if self.flash:
            self.flash -= 1
            if not self.flash:
                self.reset()
                self.last = self.frame_at
            return
        hx, hy = self.body[0]
        moves = [(hx + 1, hy), (hx - 1, hy), (hx, hy + 1), (hx, hy - 1)]
        moves = [m for m in moves if self.free(m)]
        if not moves:
            self.flash = 10  # crashed: blink, then start again
            return
        if self.food:
            fx, fy = self.food
            moves.sort(key=lambda m: abs(m[0] - fx) + abs(m[1] - fy))
        nxt = moves[0]
        self.body.insert(0, nxt)
        if nxt == self.food:
            self.place_food()
        else:
            self.body.pop()

    def render(self, b, f):
        if f < self.last:
            self.reset()
        self.frame_at = f
        while self.last < f:
            if (self.last % 2) == 0:
                self.step()
            self.last += 1
        c = self.CELL
        b.rect(0, 0, 64, 1, dim(GREY, 0.4))
        b.rect(0, 31, 64, 1, dim(GREY, 0.4))
        if self.food:
            b.rect(self.food[0] * c, self.food[1] * c, c, c, RED)
        dead = self.flash and (self.flash // 2) % 2
        for i, (x, y) in enumerate(self.body):
            if not dead:
                b.rect(x * c, y * c, c, c, WHITE if i == 0 else dim(GREEN, 1.0 - min(i, 12) * 0.04))
        b.text(1, 25, str(len(self.body) - 3), AMBER)


class Life(Cameo):
    day = False
    total = 300
    W, H, CELL = 32, 16, 2

    def __init__(self):
        Cameo.__init__(self)
        self.reset()

    def reset(self):
        self.rng = Lcg(9)
        self.last = 0
        self.age = [[0] * self.W for _ in range(self.H)]
        for y in range(self.H):
            for x in range(self.W):
                if self.rng.next(100) < 30:
                    self.age[y][x] = 1
        self.hue = self.rng.next(3)

    def alive(self):
        return sum(1 for row in self.age for v in row if v)

    def step(self):
        w, h, old = self.W, self.H, self.age
        new = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    row = old[(y + dy) % h]
                    for dx in (-1, 0, 1):
                        if (dx or dy) and row[(x + dx) % w]:
                            n += 1
                if old[y][x]:
                    if n == 2 or n == 3:
                        new[y][x] = min(old[y][x] + 1, 9)
                elif n == 3:
                    new[y][x] = 1
        self.age = new
        if self.alive() < 12:  # died out: sprinkle new life
            for _ in range(60):
                self.age[self.rng.next(h)][self.rng.next(w)] = 1

    def render(self, b, f):
        if f < self.last:
            self.reset()
        while self.last < f:
            if self.last % 4 == 0:
                self.step()
            self.last += 1
        c = self.CELL
        for y in range(self.H):
            row = self.age[y]
            for x in range(self.W):
                a = row[x]
                if a:
                    young = a < 3
                    col = (255, 255, 255) if young else ((60, 220, 120), (80, 160, 255), (255, 140, 60))[self.hue]
                    b.rect(x * c, y * c, c, c, col if a < 6 else dim(col, 0.6))
