# Drawing code for the scoreboard: tiny font, layouts and score animations.
#
# Everything draws through a PicoGraphics-style object `g` (create_pen,
# set_pen, rectangle), so it runs on the Interstate 75 and can also be
# previewed on a computer with a fake `g`.

WHITE = (230, 230, 230)
GREY = (110, 110, 110)
AMBER = (255, 190, 0)
BLUE = (110, 150, 255)
RED = (255, 30, 30)
YELLOW = (255, 200, 0)
GOLD = (255, 200, 60)
BASE_OFF = (50, 50, 50)
OUT_ON = (255, 40, 20)
OUT_OFF = (50, 15, 15)
ABS_OFF = (45, 45, 45)

# 3x5 pixel font, one int per row, 3 bits per row (bit 2 = left column).
FONT = {
    "A": (2, 5, 7, 5, 5), "B": (6, 5, 6, 5, 6), "C": (3, 4, 4, 4, 3),
    "D": (6, 5, 5, 5, 6), "E": (7, 4, 6, 4, 7), "F": (7, 4, 6, 4, 4),
    "G": (3, 4, 5, 5, 3), "H": (5, 5, 7, 5, 5), "I": (7, 2, 2, 2, 7),
    "J": (1, 1, 1, 5, 2), "K": (5, 5, 6, 5, 5), "L": (4, 4, 4, 4, 7),
    "M": (5, 7, 7, 5, 5), "N": (6, 5, 5, 5, 5), "O": (2, 5, 5, 5, 2),
    "P": (6, 5, 6, 4, 4), "Q": (2, 5, 5, 6, 3), "R": (6, 5, 6, 5, 5),
    "S": (3, 4, 2, 1, 6), "T": (7, 2, 2, 2, 2), "U": (5, 5, 5, 5, 7),
    "V": (5, 5, 5, 5, 2), "W": (5, 5, 7, 7, 5), "X": (5, 5, 2, 5, 5),
    "Y": (5, 5, 2, 2, 2), "Z": (7, 1, 2, 4, 7),
    "0": (7, 5, 5, 5, 7), "1": (2, 6, 2, 2, 7), "2": (6, 1, 2, 4, 7),
    "3": (6, 1, 2, 1, 6), "4": (5, 5, 7, 1, 1), "5": (7, 4, 6, 1, 6),
    "6": (3, 4, 7, 5, 7), "7": (7, 1, 2, 2, 2), "8": (7, 5, 7, 5, 7),
    "9": (7, 5, 7, 1, 6),
    " ": (0, 0, 0, 0, 0), "-": (0, 0, 7, 0, 0), ":": (0, 2, 0, 2, 0),
    "/": (1, 1, 2, 4, 4), "!": (2, 2, 2, 0, 2), ".": (0, 0, 0, 0, 2),
    "+": (0, 2, 7, 2, 0), "@": (7, 5, 5, 4, 3), "|": (2, 2, 2, 2, 2),
    "?": (6, 1, 2, 0, 2), ",": (0, 0, 0, 2, 4), "'": (2, 2, 0, 0, 0),
    "(": (1, 2, 2, 2, 1), ")": (4, 2, 2, 2, 4), "&": (2, 5, 2, 5, 3),
    "=": (0, 7, 0, 7, 0),
    "^": (2, 7, 0, 0, 0),  # top of an inning
    "v": (0, 0, 0, 7, 2),  # bottom of an inning
}


def text_width(s, scale=1):
    return len(s) * 4 * scale - scale if s else 0


def dim(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


class Board:
    def __init__(self, g, width, height):
        self.g = g
        self.w = width
        self.h = height
        self._pens = {}
        self._clip = (0, height)
        self.bright = 1.0

    # -- primitives ------------------------------------------------------
    def _pen(self, c):
        p = self._pens.get(c)
        if p is None:
            if len(self._pens) > 150:
                self._pens.clear()
            d = c if self.bright >= 1.0 else dim(c, self.bright)
            p = self._pens[c] = self.g.create_pen(d[0], d[1], d[2])
        return p

    def set_brightness(self, f):
        """Scale every colour (night mode). 1.0 = full."""
        if f != self.bright:
            self.bright = f
            self._pens.clear()

    def rect(self, x, y, w, h, c):
        y0, y1 = self._clip
        x1 = min(x + w, self.w)
        x = max(x, 0)
        y1 = min(y + h, y1)
        y = max(y, y0)
        if x1 <= x or y1 <= y:
            return
        self.g.set_pen(self._pen(c))
        self.g.rectangle(x, y, x1 - x, y1 - y)

    def text(self, x, y, s, c, scale=1):
        for ch in s:
            rows = FONT.get(ch)
            if rows is None:
                rows = FONT.get(ch.upper(), FONT[" "])
            if x >= self.w:
                break
            if x + 3 * scale > 0:
                for ry in range(5):
                    bits = rows[ry]
                    if not bits:
                        continue
                    for cx in range(3):
                        if bits & (4 >> cx):
                            self.rect(x + cx * scale, y + ry * scale, scale, scale, c)
            x += 4 * scale

    def segments(self, x, y, parts, scale=1):
        """Draw (text, colour) parts left to right with one space between."""
        for s, c in parts:
            if not s:
                continue
            self.text(x, y, s, c, scale)
            x += text_width(s, scale) + 4 * scale

    def clear(self):
        self._clip = (0, self.h)
        self.rect(0, 0, self.w, self.h, (0, 0, 0))

    # -- layouts ---------------------------------------------------------
    def regions(self, n):
        """Split the panel into n horizontal bands: [(y0, y1), ...]."""
        step = self.h // n
        out = []
        for i in range(n):
            y0 = i * step
            out.append((y0, self.h if i == n - 1 else y0 + step))
        return out

    def draw_games(self, views):
        """Draw every game; `views` is a list of dicts built by main.make_view."""
        self.clear()
        n = len(views)
        if n == 0:
            return
        for i, (y0, y1) in enumerate(self.regions(n)):
            self._clip = (y0, y1)
            v = views[i]
            if n == 1:
                (self._draw_ball_full if "live" in v else self._draw_full)(v, y0)
            elif n == 2:
                (self._draw_ball_half if "live" in v else self._draw_half)(v, y0)
            else:
                self._draw_compact(v, y0, y1)
            if i:
                self.rect(0, y0, self.w, 1, (35, 35, 35))
        self._clip = (0, self.h)

    def _side_colors(self, v):
        ours = v["ours"]
        return (v["color"] if ours == "away" else WHITE,
                v["color"] if ours == "home" else WHITE)

    def _draw_full(self, v, y0):
        self.text(1, y0 + 1, v["status"], v["status_color"])
        if v.get("tag"):
            self.text(self.w - 1 - text_width(v["tag"]), y0 + 1, v["tag"], GOLD)
        ca, ch = self._side_colors(v)
        for k, (label, score, col) in enumerate(
                ((v["away"], v["away_score"], ca), (v["home"], v["home_score"], ch))):
            y = y0 + 8 + k * 12
            self.rect(0, y, 1, 10, col if col != WHITE else GREY)
            self.text(4, y, label, col, 2)
            if score is not None:
                s = str(score)
                self.text(self.w - 1 - text_width(s, 2), y, s, WHITE, 2)

    def _plus(self, cx, cy, c):
        """A base: 3x3 plus shape, which reads as a diamond at this size."""
        self.rect(cx - 1, cy, 3, 1, c)
        self.rect(cx, cy - 1, 1, 3, c)

    def _abs_squares(self, x, y, remaining, c, size, gap, vertical):
        """Two ABS challenge squares; filled for each challenge still available."""
        for i in range(2):
            on = remaining is not None and i < remaining
            off = i * (size + gap)
            self.rect(x if vertical else x + off, y + off if vertical else y,
                      size, size, c if on else ABS_OFF)

    def _draw_ball_full(self, v, y0):
        live = v["live"]
        self.text(5, y0 + 1, v["status"], v["status_color"])
        self.text(5 + text_width(v["status"]) + 4, y0 + 1, live["count"], GREY)
        ca, ch = self._side_colors(v)
        for k, (side, label, col) in enumerate((("away", v["away"], ca), ("home", v["home"], ch))):
            y = y0 + 8 + k * 12
            s = str(v[side + "_score"])
            self.text(5, y, label, col, 2)
            self.text(44 - text_width(s, 2), y, s, WHITE, 2)
            if live["abs"]:
                self._abs_squares(0, y + 1, live["abs"][side], v["color"] if v["ours"] == side else WHITE,
                                  3, 2, True)
        b = live["bases"]
        self._plus(54, y0 + 5, YELLOW if b[1] else BASE_OFF)
        self._plus(48, y0 + 11, YELLOW if b[2] else BASE_OFF)
        self._plus(60, y0 + 11, YELLOW if b[0] else BASE_OFF)
        for i in range(3):
            self.rect(48 + i * 5, y0 + 17, 2, 2, OUT_ON if i < live["outs"] else OUT_OFF)
        self.text(50, y0 + 22, "OUT", GREY)

    def _draw_ball_half(self, v, y0):
        live = v["live"]
        ca, ch = self._side_colors(v)
        for k, (side, label, col) in enumerate((("away", v["away"], ca), ("home", v["home"], ch))):
            y = y0 + 2 + k * 7
            self.segments(1, y, [(label, col), (str(v[side + "_score"]), WHITE)])
            if live["abs"]:
                self._abs_squares(32, y + 1, live["abs"][side], v["color"] if v["ours"] == side else WHITE,
                                  3, 1, False)
        b = live["bases"]
        for on, x, y in ((b[1], 54, 1), (b[2], 50, 4), (b[0], 58, 4)):
            self.rect(x, y0 + y, 2, 2, YELLOW if on else BASE_OFF)
        for i in range(3):
            self.rect(50 + i * 4, y0 + 8, 2, 1, OUT_ON if i < live["outs"] else OUT_OFF)
        st = v["status"]
        self.text(self.w - 1 - text_width(st), y0 + 10, st, v["status_color"])

    def _draw_half(self, v, y0):
        ca, ch = self._side_colors(v)
        parts = [(v["away"], ca)]
        if v["away_score"] is not None:
            parts += [(str(v["away_score"]), WHITE)]
        parts += [(v["home"], ch)]
        if v["home_score"] is not None:
            parts += [(str(v["home_score"]), WHITE)]
        self.segments(1, y0 + 2, parts)
        self.text(1, y0 + 9, v["status"], v["status_color"])
        if v.get("tag"):
            self.text(self.w - 1 - text_width(v["tag"]), y0 + 9, v["tag"], GOLD)

    def _draw_compact(self, v, y0, y1):
        ca, ch = self._side_colors(v)
        parts = [(v["away"], ca)]
        if v["away_score"] is not None:
            parts += [(str(v["away_score"]), WHITE)]
        parts += [(v["home"], ch)]
        if v["home_score"] is not None:
            parts += [(str(v["home_score"]), WHITE)]
        used = sum(text_width(s) + 4 for s, _ in parts)
        if used + text_width(v["short"]) <= self.w:
            parts.append((v["short"], v["status_color"]))
        self.segments(1, y0 + (y1 - y0 - 5) // 2 + 1, parts)

    def draw_message(self, lines, region=None, backdrop=None):
        """Centred lines of (text, colour), inside region (y0, y1) or the whole panel."""
        y0, y1 = region or (0, self.h)
        self._clip = (y0, y1)
        self.rect(0, y0, self.w, y1 - y0, (0, 0, 0))
        if backdrop:
            backdrop(y0, y1)
        step = 7
        top = y0 + (y1 - y0 - step * len(lines) + 2) // 2
        for i, (s, c) in enumerate(lines):
            if isinstance(s, list):  # several (text, colour) parts on one line
                w = sum(text_width(t) for t, _ in s) + 4 * (len(s) - 1)
                self.segments((self.w - w) // 2, top + i * step, s)
            else:
                self.text((self.w - text_width(s)) // 2, top + i * step, s, c)
        self._clip = (0, self.h)

    # -- clock and weather -----------------------------------------------
    def weather_icon(self, kind, x, y):
        """5x5 weather icon: sun, cloud, rain, snow or storm."""
        if kind == "sun":
            self.rect(x + 1, y + 1, 3, 3, YELLOW)
            for rx, ry in ((2, 0), (2, 4), (0, 2), (4, 2)):
                self.rect(x + rx, y + ry, 1, 1, dim(YELLOW, 0.5))
            return
        cloud = (170, 175, 195)
        self.rect(x + 1, y + 1, 3, 1, cloud)
        self.rect(x, y + 2, 5, 2, cloud)
        if kind == "rain":
            self.rect(x + 1, y + 4, 1, 1, (90, 150, 255))
            self.rect(x + 3, y + 4, 1, 1, (90, 150, 255))
        elif kind == "snow":
            self.rect(x + 1, y + 4, 1, 1, WHITE)
            self.rect(x + 3, y + 4, 1, 1, WHITE)
        elif kind == "storm":
            self.rect(x + 2, y + 4, 1, 1, YELLOW)

    def weather_fx(self, kind, f, y0, y1):
        """Rain or snow falling behind the text of the clock slide."""
        if kind not in ("rain", "snow", "storm"):
            return
        h = y1 - y0
        c = (35, 55, 110) if kind != "snow" else (70, 75, 100)
        for k in range(14):
            x = (k * 23 + 5) % 64
            y = (f * (2 if kind != "snow" else 1) + k * 7) % h
            self.rect(x + (f // 6 + k) % 2 * (kind == "snow"), y0 + y, 1, 2 if kind != "snow" else 1, c)

    def draw_clock(self, region, hhmm, ap, date, wx, f=0):
        """Clock slide: big time, date, then weather icon + temperature."""
        y0, y1 = region
        self._clip = (y0, y1)
        self.rect(0, y0, self.w, y1 - y0, (0, 0, 0))
        if wx:
            self.weather_fx(wx[0], f, y0, y1)
        tw = text_width(hhmm, 2) + 5
        x = (self.w - tw) // 2
        self.text(x, y0 + 2, hhmm, WHITE, 2)
        self.text(x + tw - 3, y0 + 7, ap, GREY)
        self.text((self.w - text_width(date)) // 2, y0 + 14, date, AMBER)
        if wx:
            t = wx[1]
            w = 7 + text_width(t)
            x = (self.w - w) // 2
            self.weather_icon(wx[0], x, y0 + 19)
            self.text(x + 7, y0 + 19, t, BLUE)
        self._clip = (0, self.h)

    @staticmethod
    def marquee_width(parts):
        return sum(text_width(s) + 4 for s, _ in parts)

    def draw_marquee(self, parts, offset, region, clear=True):
        """Scrolling ticker: parts is [(text, colour)], offset pixels scrolled so far.
        clear=False draws the text over whatever is already there (used over cameos)."""
        y0, y1 = region
        self._clip = (y0, y1)
        if clear:
            self.rect(0, y0, self.w, y1 - y0, (0, 0, 0))
        y = y0 + (y1 - y0 - 5) // 2
        x = self.w - offset
        for s, c in parts:
            w = text_width(s)
            if x >= self.w:
                break
            if x + w > 0:
                self.text(x, y, s, c)
            x += w + 4
        self._clip = (0, self.h)

    # -- animation -------------------------------------------------------
    def draw_anim(self, a, region):
        """Draw frame a.frame of animation `a` inside region (y0, y1)."""
        y0, y1 = region
        h = y1 - y0
        self._clip = (y0, y1)
        f, total = a.frame, a.total
        p = f / total
        col = a.color
        self.rect(0, y0, self.w, h, (0, 0, 0))
        if a.mood:
            self._draw_mood(a, y0, h, f, p)
            self._clip = (0, self.h)
            return

        # opening flash
        if a.ours and f < 10 and (f // 3) % 2 == 0:
            self.rect(0, y0, self.w, h, dim(col, 0.45))

        # bands of light flowing left to right
        band = 16
        for k in range(3):
            pos = f * 2.6 - k * 34 - band
            for x in range(int(pos) - band, int(pos) + band, 1):
                if x < 0 or x >= self.w:
                    continue
                inten = 1.0 - abs(x - pos) / band
                if inten > 0:
                    self.rect(x, y0, 1, h, dim(col, 0.15 + 0.7 * inten * (1.0 if a.ours else 0.5)))

        if a.ours:
            self._accent(a, y0, h, f, total)

        # banner text scrolling through
        scale = 2 if h >= 24 else 1
        tw = text_width(a.text, scale)
        ty = y0 + (h - 5 * scale) // 2
        if tw <= self.w - 2:
            centre = (self.w - tw) // 2
            if p < 0.3:
                x = int(self.w + (centre - self.w) * (p / 0.3))
            elif p < 0.78:
                x = centre
            else:
                x = int(centre - (centre + tw) * ((p - 0.78) / 0.22))
        else:
            x = int(self.w - (self.w + tw) * p)
        self.text(x + 1, ty + 1, a.text, (0, 0, 0), scale)
        self.text(x, ty, a.text, WHITE, scale)
        self._clip = (0, self.h)

    CONFETTI = ((255, 60, 60), (255, 200, 0), (90, 220, 90), (90, 150, 255), (255, 110, 200))

    def _draw_mood(self, a, y0, h, f, p):
        """End-of-game mood: confetti for a win, grey rain for a loss."""
        win = a.mood == "win"
        for k in range(36 if win else 24):
            x = (k * 29 + 3) % self.w
            if win:
                y = (f * (1 + k % 3) // 2 + k * 5) % (h + 4) - 2
                x += (f // 5 + k) % 3 - 1
                self.rect(x, y0 + y, 2, 2, self.CONFETTI[k % 5])
            else:
                y = (f * 2 + k * 7) % (h + 2)
                self.rect(x, y0 + y, 1, 2, (50, 60, 90))
        scale = 2 if h >= 24 and text_width(a.text, 2) <= self.w - 2 else 1
        tx = (self.w - text_width(a.text, scale)) // 2
        ty = y0 + (h - 5 * scale) // 2
        if win and (f // 4) % 2:
            c = a.color
        else:
            c = WHITE if win else (130, 140, 190)
        if min(f, a.total - f) < 12:  # slide the banner in and out
            ty += 12 - min(f, a.total - f)
        self.text(tx + 1, ty + 1, a.text, (0, 0, 0), scale)
        self.text(tx, ty, a.text, c, scale)

    def _accent(self, a, y0, h, f, total):
        sport = a.sport
        span = self.w + 10
        bx = int(f * span / total * 1.1) - 5
        if sport == "hockey":
            if (f // 4) % 2 == 0:
                self.rect(0, y0, 2, h, RED)
                self.rect(self.w - 2, y0, 2, h, RED)
            # puck skidding along the ice
            self.rect(bx, y0 + h - 2, 3, 1, (20, 20, 20))
            self.rect(bx - 6, y0 + h - 2, 5, 1, GREY)
        elif sport == "football":
            cy = y0 + h // 2
            for t in range(1, 6):
                self.rect(bx - t * 3, cy, 2, 1, dim(WHITE, 0.6 - t * 0.1))
            self.rect(bx, cy - 1, 3, 2, (190, 100, 30))
        else:  # baseball: ball arcing over the screen
            q = (f / total) * 1.1
            arc = 4 * q * (1 - q) if 0 < q < 1 else 0
            by = y0 + h - 2 - int(arc * (h - 3))
            for t in range(1, 5):
                px = bx - t * 3
                py = y0 + h - 2 - int((4 * ((px + 5) / span) * (1 - (px + 5) / span)
                                       if 0 < (px + 5) < span else 0) * (h - 3))
                self.rect(px, py, 1, 1, dim(WHITE, 0.5 - t * 0.1))
            self.rect(bx, by, 2, 2, WHITE)


class Anim:
    def __init__(self, game_key, sport, color, text, ours, total=110, mood=None):
        self.cameo = None   # a critters.Cameo to play full-panel instead of the banner
        self.mood = mood    # "win" / "loss" for end-of-game moods, None for score banners
        self.key = game_key
        self.sport = sport
        self.color = color
        self.text = text
        self.ours = ours
        self.frame = 0
        self.total = total

    @property
    def done(self):
        return self.frame >= self.total
