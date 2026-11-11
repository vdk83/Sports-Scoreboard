# ESPN scoreboard reader for MicroPython.
#
# ESPN's scoreboard JSON is far too big to json.loads() on a microcontroller
# (the NFL one is 250KB+), so the response is streamed in small chunks and
# only the handful of fields we need are plucked out of each event.
import gc
import socket
import time

try:
    import select
except ImportError:
    import uselect as select

HOST = "site.api.espn.com"
PATH = "/apis/site/v2/sports/%s/scoreboard"
CHUNK = 2048
LOOKBACK = 300  # event "date" sits just before its "shortName"
ANCHOR = b'"shortName":"'


_ACCENTS = {"á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a", "å": "a", "é": "e", "è": "e", "ê": "e", "ë": "e",
            "í": "i", "ì": "i", "î": "i", "ï": "i", "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o", "ø": "o",
            "ú": "u", "ù": "u", "û": "u", "ü": "u", "ñ": "n", "ç": "c", "ý": "y", "č": "c", "ć": "c", "š": "s",
            "ž": "z", "ł": "l", "ń": "n", "ř": "r", "ś": "s", "ğ": "g", "ş": "s", "ı": "i"}
_SUFFIXES = ("JR", "SR", "II", "III", "IV")


def last_name(full):
    """'Julio Rodríguez Jr.' -> 'RODRIGUEZ': the family name in capitals the panel's font can draw."""
    if "\\u" in full:  # the feed escaped non-ASCII letters
        try:
            import json
            full = json.loads('"%s"' % full)
        except ValueError:
            pass
    parts = full.replace(",", " ").split()
    while len(parts) > 1 and parts[-1].upper().strip(".") in _SUFFIXES:
        parts.pop()
    out = ""
    for ch in (parts[-1] if parts else "").lower():
        ch = _ACCENTS.get(ch, ch)
        if "a" <= ch <= "z" or ch in "-'.":
            out += ch
    return out.upper()


def _event_anchor(buf, start):
    # An event's shortName looks like "KC @ SEA" or "TOR VS BOS"; player
    # shortNames ("C. Williams") never contain " @ " or " VS ".
    while True:
        a = buf.find(ANCHOR, start)
        if a < 0:
            return -1
        e = buf.find(b'"', a + 13)
        if e < 0:
            return -1
        s = buf[a + 13:e]
        if b" @ " in s or b" VS " in s or b" vs. " in s:  # hockey home games read "CAR vs. SEA"
            return a
        start = a + 13


def _str(rec, key, pos=0):
    i = rec.find(key, pos)
    if i < 0:
        return None, pos
    i += len(key)
    j = rec.find(b'"', i)
    return rec[i:j].decode(), j


def parse_event(rec, date, sport, eid=""):
    """Pull the fields we care about out of one event's raw JSON bytes."""
    name, p = _str(rec, ANCHOR)
    if name is None:
        return None
    teams = {}
    ids = {}
    for _ in range(2):
        h = rec.find(b'"homeAway":"', p)
        if h < 0:
            return None
        side = "home" if rec[h + 12:h + 13] == b"h" else "away"
        nxt = rec.find(b'"homeAway":"', h + 12)  # this team's entry ends where the other one starts
        tid, t = _str(rec, b'"team":{"id":"', h)
        ids[tid] = side
        # The abbreviation must come from inside "team": a record in the entry can also have an
        # "abbreviation" ("Total"), and ESPN's soccer feed lists the records before the team.
        abbr, p = _str(rec, b'"abbreviation":"', t)
        sc, q = _str(rec, b'"score":"', h)  # the score may sit before or after the team
        if sc is None or (0 <= nxt < q):
            sc = "0"
        else:
            p = max(p, q)
        teams[side] = (abbr, int(sc) if sc.isdigit() else 0)
    if len(teams) != 2:
        return None

    clock, p = _str(rec, b'"displayClock":"', p)
    period = 0
    k = rec.find(b'"period":', p)
    if k >= 0:
        k += 9
        e = k
        while e < len(rec) and 48 <= rec[e] <= 57:
            e += 1
        period = int(rec[k:e]) if e > k else 0
    state, p2 = _str(rec, b'"state":"', p)
    detail, p3 = _str(rec, b'"shortDetail":"', p2)
    i = rec.find(b'"season":{')
    playoff = i >= 0 and b"post-season" in rec[i:i + 90]
    note = ""
    n = rec.find(b'"notes":[{')
    if n >= 0:
        h = rec.find(b'"headline":"', n)
        if 0 <= h - n < 60:
            note = _str(rec, b'"headline":"', n)[0] or ""
    qb = None
    if sport == "football" and state == "in":
        qb = _passing_leader(rec, ids)
    return {
        "sport": sport,
        "id": eid,
        "name": name,
        "date": date,
        "away": teams["away"][0],
        "away_score": teams["away"][1],
        "home": teams["home"][0],
        "home_score": teams["home"][1],
        "clock": clock or "",
        "period": period,
        "state": state or "pre",
        "detail": detail or "",
        "playoff": playoff,
        "note": note,
        "qb": qb,
    }


def _passing_leader(rec, ids):
    """The game's passing leader as (last name, passing yards, 'away'/'home'), or None."""
    k = rec.find(b'"name":"passingYards","displayName":"Passing Leader"')
    if k < 0:
        return None
    text, p = _str(rec, b'"displayValue":"', k)   # like "16/26, 242 YDS, 1 TD"
    name, p = _str(rec, b'"shortName":"', p)
    tid = _str(rec, b'"team":{"id":"', p)[0]
    if not text or not name or tid not in ids:
        return None
    yds = ""
    for part in text.split(","):
        if part.strip().endswith("YDS"):
            yds = part.strip().split()[0]
    return (last_name(name), int(yds) if yds.isdigit() else 0, ids[tid])


def _scan(read, sport, wanted, stop_after_first):
    games = []
    buf = b""
    eof = False
    while True:
        if not eof:
            chunk = read(CHUNK)
            if chunk:
                buf += chunk
            else:
                eof = True
        t_work = time.ticks_ms()
        while True:
            a0 = _event_anchor(buf, 0)
            if a0 < 0:
                buf = buf[-LOOKBACK:]
                break
            if a0 > LOOKBACK:
                buf = buf[a0 - LOOKBACK:]
                a0 = LOOKBACK
            a1 = _event_anchor(buf, a0 + 14)
            if a1 < 0 and not eof:
                if len(buf) > 80000:  # runaway; give up on this event
                    buf = buf[a0 + 14:]
                    continue
                break
            end = a1 if a1 >= 0 else len(buf)
            rec = buf[a0:end]
            name = rec[13:rec.find(b'"', 13)]
            if wanted is None or any(t.encode() in name.split() for t in wanted):
                d = buf.rfind(b'"date":"', 0, a0)
                date = buf[d + 8:d + 25].decode() if d >= 0 else ""
                i = buf.rfind(b'"id":"', 0, d) if d >= 0 else -1
                eid = buf[i + 6:buf.find(b'"', i + 6)].decode() if i >= 0 else ""
                g = parse_event(rec, date, sport, eid)
                if g:
                    games.append(g)
                    if stop_after_first:
                        return games
            if a1 < 0:
                buf = b""
                break
            buf = buf[max(0, a1 - LOOKBACK):]
        dt = time.ticks_diff(time.ticks_ms(), t_work)
        if dt > 150:
            print("timing: scanning one chunk took", dt, "ms; buffer", len(buf))
        if eof:
            return games


# -- plain-HTTP client that never blocks the display ------------------------
# Scores are public data, so plain HTTP is fine, and it skips the TLS handshake
# (about a second of pure computation, which froze the ticker). Every wait on
# the network calls the tick hook so the caller can keep drawing frames.
CONNECT_MS = 8000   # give up connecting after this long
IDLE_MS = 10000     # give up when no data arrives for this long
where = ""      # what the network code is doing right now (shown if the display stalls)
_tick = None
_addrs = {}         # host -> resolved address: DNS can stall, so look it up once


def set_tick(fn):
    """fn(waiting) is called often during network work; it should draw a frame if one is due
    (and sleep a moment if `waiting`) and return quickly."""
    global _tick
    _tick = fn


def _wait():
    """Idle until the network has something for us, keeping the display going."""
    if _tick:
        _tick(True)
    else:
        time.sleep_ms(2)


def _pump():
    """Called between chunks of data: with a fast connection there may be nothing to wait for."""
    if _tick:
        _tick(False)


def _again(e):
    return bool(e.args) and e.args[0] in (11, 115, 119)  # EAGAIN, EINPROGRESS


def resolve(host):
    addr = _addrs.get(host)
    if addr is None:
        addr = _addrs[host] = socket.getaddrinfo(host, 80, 0, socket.SOCK_STREAM)[0][-1]
    return addr


class Conn:
    def __init__(self, s):
        self.s = s
        self.eof = False

    def read(self, n):
        """Up to n bytes; b"" at the end. Keeps the display going while it waits."""
        global where
        if self.eof:
            return b""
        where = "read"
        _pump()
        t0 = time.ticks_ms()
        while True:
            try:
                d = self.s.read(n)  # non-blocking: None means nothing yet
            except OSError as e:
                if not _again(e):
                    raise
                d = None
            if d is None:
                if time.ticks_diff(time.ticks_ms(), t0) > IDLE_MS:
                    raise OSError(110)
                _wait()
                continue
            if not d:
                self.eof = True
            where = "parse"
            return d

    def close(self):
        global where
        where = "close"
        t = time.ticks_ms()
        try:
            self.s.close()
        except Exception:
            pass
        dt = time.ticks_diff(time.ticks_ms(), t)
        if dt > 150:
            print("timing: socket close took", dt, "ms")


def _open(host, path):
    """GET http://host/path. Returns (connection, first bytes of the body)."""
    global where
    s = None
    try:
        where = "dns"
        addr = resolve(host)
        where = "connect"
        s = socket.socket()
        s.setblocking(False)
        try:
            s.connect(addr)
        except OSError as e:
            if not _again(e):
                raise
        p = select.poll()
        p.register(s, select.POLLOUT)
        t0 = time.ticks_ms()
        while True:
            ev = p.poll(0)
            if ev:
                if ev[0][1] & (select.POLLERR | select.POLLHUP):
                    raise OSError(111)
                break
            if time.ticks_diff(time.ticks_ms(), t0) > CONNECT_MS:
                raise OSError(110)
            _wait()
        # HTTP/1.0 so the server doesn't use chunked transfer encoding.
        req = ("GET %s HTTP/1.0\r\nHost: %s\r\nUser-Agent: interstate75\r\n"
               "Accept: application/json\r\n\r\n" % (path, host)).encode()
        off = 0
        while off < len(req):
            try:
                n = s.write(req[off:])
            except OSError as e:
                if not _again(e):
                    raise
                n = None
            if n:
                off += n
            else:
                _wait()
        conn = Conn(s)
        head = b""
        while b"\r\n\r\n" not in head:
            d = conn.read(256)
            if not d:
                raise OSError("no response")
            head += d
            if len(head) > 4096:
                raise OSError("bad headers")
        hdr, _, body = head.partition(b"\r\n\r\n")
        if b" 200" not in hdr.split(b"\r\n")[0]:
            raise OSError(hdr.split(b"\r\n")[0])
        return conn, body
    except BaseException:
        _addrs.pop(host, None)  # the address may have changed; look it up again next time
        if s:
            try:
                s.close()
            except Exception:
                pass
        raise


def fetch(sport, league_path, teams, stop_after_first=False):
    """Return a list of game dicts involving `teams` for one league."""
    gc.collect()
    s, body = _open(HOST, PATH % league_path)
    pending = [body]

    def read(n):
        if pending:
            return pending.pop()
        return s.read(n)

    try:
        return _scan(read, sport, teams, stop_after_first)
    finally:
        s.close()
        gc.collect()


TEAM_PATH = "/apis/site/v2/sports/%s/teams/%s"


class _TeamPage:
    """Picks the next game and the record out of a team page (~25KB) as it streams past, keeping only a
    few small pieces: the page is too big to hold at once once the board's memory has fragmented."""
    TAIL = 40
    REC_MAX = 1600

    def __init__(self):
        self.tail = b""
        self.on = False     # the "nextEvent" part has started
        self.date = None
        self.name = None
        self.valid = None
        self.rec = None     # bytes after the record marker, until REC_MAX
        self.rec_done = False

    def add(self, chunk):
        win = self.tail + chunk
        self.tail = win[-self.TAIL:]
        if self.rec is None:
            i = win.find(b'"record":{"items":[')
            if i >= 0:
                self.rec = win[i:i + self.REC_MAX]
        elif len(self.rec) < self.REC_MAX:
            self.rec += chunk[:self.REC_MAX - len(self.rec)]
        if not self.on:
            i = win.find(b'"nextEvent":[')
            if i < 0:
                return
            self.on = True
            win = win[i:]
        if self.date is None:
            i = win.find(b'"date":"')
            if i >= 0 and win.find(b'"', i + 8) > i + 8 + 10:  # all of it has arrived
                self.date = _str(win, b'"date":"')[0]
        if self.valid is None:
            i = win.find(b'"timeValid":')
            if i >= 0 and len(win) > i + 17:
                self.valid = win[i + 12:i + 17] != b"false"
        if self.name is None:
            pos = 0
            while True:
                a = _event_anchor(win, pos)
                if a < 0:
                    break
                self.name = _str(win, ANCHOR, a - 1)[0]
                break

    def done(self):
        return (self.name and self.date and self.valid is not None and self.rec is not None
                and len(self.rec) >= self.REC_MAX)

    def result(self):
        if not self.name or not self.date:
            return None
        record, streak = None, 0
        r = self.rec
        if r:
            k = r.find(b'"name":"streak","value":')
            if k >= 0:
                try:
                    streak = int(float(r[k + 24:k + 34].split(b"}")[0]))
                except ValueError:
                    pass
            k = r.find(b'"summary":"')
            if k >= 0:
                record = str(r[k + 11:k + 20].split(b'"')[0], "utf-8")
        return {"date": self.date[:16] + "Z", "name": self.name.replace(" vs. ", " VS "), "time_valid": self.valid is not False,
                "record": record, "streak": streak}


def next_event(league_path, slug):
    """A team's next scheduled game from its ESPN team page.

    Returns {"date", "name", "time_valid", "record", "streak"} or None. The page streams past in small
    pieces (see _TeamPage), so this needs only a few KB however fragmented the memory is."""
    gc.collect()
    s, body = _open(HOST, TEAM_PATH % (league_path, slug))
    page = _TeamPage()
    n = len(body)
    try:
        page.add(body)
        while n < 60000 and not page.done():
            d = s.read(1024)
            if not d:
                break
            n += len(d)
            page.add(d)
    finally:
        s.close()
    gc.collect()
    return page.result()
