# League headlines for the idle ticker (ESPN news feed, plain HTTP). Streamed and capped so it costs little RAM.
import gc

import espn

HOST = "site.api.espn.com"
PATH = "/apis/site/v2/sports/%s/news?limit=4"
LIMIT = 40000      # bytes read at most
KEEP = 3           # headlines per league
MAX_CHARS = 90
KEY = b'"headline":"'
OK = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?!'-()&: "


def clean(text):
    """Panel-safe capitals: only characters the font has."""
    out = ""
    for c in text.upper().replace("’", "'").replace("—", "-").replace("–", "-"):
        if c in OK:
            out += c
    out = " ".join(out.split())
    if len(out) > MAX_CHARS:
        out = out[:MAX_CHARS].rsplit(" ", 1)[0]
    return out


class Scan:
    """Finds headline strings in a stream, whatever the chunk size."""

    def __init__(self):
        self.buf = b""
        self.found = []

    @property
    def done(self):
        return len(self.found) >= KEEP

    def add(self, chunk):
        self.buf += chunk
        while not self.done:
            i = self.buf.find(KEY)
            if i < 0:
                self.buf = self.buf[-len(KEY):]
                return
            j = i + len(KEY)
            k = j
            while True:  # the closing quote that is not escaped
                k = self.buf.find(b'"', k)
                if k < 0 or self.buf[k - 1:k] != b"\\":
                    break
                k += 1
            if k < 0:
                self.buf = self.buf[i:]
                return
            raw = self.buf[j:k]
            self.buf = self.buf[k:]
            try:
                text = clean(raw.decode("utf-8").replace('\\"', '"').replace("\\u2019", "'"))
            except (UnicodeError, ValueError):
                continue
            if len(text) > 12 and text not in self.found:
                self.found.append(text)


def fetch(path):
    """Up to KEEP headlines for a league path such as 'hockey/nhl'."""
    s, body = espn._open(HOST, PATH % path)
    scan = Scan()
    got = len(body)
    try:
        scan.add(body)
        while not scan.done and got < LIMIT:
            d = s.read(1024)
            if not d:
                break
            got += len(d)
            scan.add(d)
    finally:
        s.close()
    gc.collect()
    return scan.found
