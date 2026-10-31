# Update over WiFi. A tiny HTTP server on port 8080; deploy.py on the computer talks to it.
#
#   GET  /hashes     sha256 of every .py file on the board (so deploy.py sends only what changed)
#   GET  /status     uptime, free memory, WiFi signal
#   PUT  /f/<name>   upload one file (header X-Sha256 = its hash); it waits as <name>.tmp
#   POST /apply      swap the uploaded files in (old ones kept as <name>.bak) and restart
#   POST /clear      throw away uploads that were not applied
#
# Every request needs the header X-Key: <OTA_KEY from secrets.py on the board>.
# If an update leaves the board unable to start three times in a row, main.py puts the .bak files back.
import binascii
import gc
import hashlib
import os
import socket
import time

import machine
import network

PORT = 8080
PROTECTED = ("secrets.py", "main.py")  # never replaced over WiFi
TRY_FILE = "ota_try"


def _hex(h):
    return binascii.hexlify(h.digest()).decode()


def _name_ok(name):
    return (name.endswith(".py") and "/" not in name and "." not in name[:-3] and 0 < len(name) < 32
            and name not in PROTECTED)


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            d = f.read(512)
            if not d:
                break
            h.update(d)
    return _hex(h)


def healthy():
    """Called once the new code has run fine for a while: forget the rollback marker."""
    try:
        os.remove(TRY_FILE)
    except OSError:
        pass


class Server:
    def __init__(self, key, feed, show):
        self.key = key
        self.feed = feed
        self.show = show  # called when an upload starts (puts a message on the panel)
        self.t0 = time.ticks_ms()
        self.sock = None
        self.bind()

    def bind(self):
        """(Re)open the listening socket. Done every few minutes because it can go deaf after WiFi drops."""
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", PORT))
        s.listen(1)
        s.setblocking(False)
        self.sock = s
        self.bound = time.ticks_ms()

    def poll(self):
        """Check for a visitor. True if one was served (the display needs a redraw after)."""
        if time.ticks_diff(time.ticks_ms(), self.bound) > 180000:
            try:
                self.bind()
            except OSError as e:
                print("ota rebind:", repr(e))
                self.bound = time.ticks_ms()
        try:
            c, _ = self.sock.accept()
        except OSError:
            return False
        c.settimeout(2)
        try:
            self.handle(c)
        except Exception as e:
            print("ota:", repr(e))
            self.reply(c, 500, repr(e))
        try:
            c.close()
        except OSError:
            pass
        gc.collect()
        return True

    def reply(self, c, code, body=""):
        try:
            c.send("HTTP/1.0 %d X\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s" % (code, len(body), body))
        except OSError:
            pass

    def handle(self, c):
        buf = b""
        while b"\r\n\r\n" not in buf:
            d = c.recv(512)
            if not d or len(buf) > 2048:
                return
            buf += d
        head, _, body = buf.partition(b"\r\n\r\n")
        lines = head.decode().split("\r\n")
        method, path = lines[0].split(" ")[:2]
        hdr = {}
        for ln in lines[1:]:
            k, _, v = ln.partition(":")
            hdr[k.strip().lower()] = v.strip()
        if hdr.get("x-key") != self.key:
            return self.reply(c, 403, "bad key")
        if method == "GET" and path == "/hashes":
            out = "".join("%s %s\n" % (f, file_hash(f)) for f in sorted(os.listdir())
                          if f.endswith(".py") and _name_ok(f))
            return self.reply(c, 200, out)
        if method == "GET" and path == "/status":
            w = network.WLAN(network.STA_IF)
            gc.collect()
            return self.reply(c, 200, "up %ds free %d rssi %s\n" % (
                time.ticks_diff(time.ticks_ms(), self.t0) // 1000, gc.mem_free(), w.status("rssi")))
        if method == "PUT" and path.startswith("/f/"):
            return self.put(c, path[3:], hdr, body)
        if method == "POST" and path == "/clear":
            self.clear()
            return self.reply(c, 200, "cleared")
        if method == "POST" and path == "/apply":
            return self.apply(c)
        self.reply(c, 404, "no")

    def put(self, c, name, hdr, body):
        if not _name_ok(name):
            return self.reply(c, 400, "bad name")
        size = int(hdr.get("content-length", "-1"))
        want = hdr.get("x-sha256", "")
        if size < 1 or size > 60000 or len(want) != 64:
            return self.reply(c, 400, "bad size or hash")
        self.show()
        tmp = name + ".tmp"
        h = hashlib.sha256()
        got = 0
        idle = 0
        pending = b""
        with open(tmp, "wb") as f:
            while True:
                if body:
                    h.update(body)
                    got += len(body)
                    pending += body
                    if len(pending) >= 2048 or got >= size:  # fewer, bigger flash writes
                        f.write(pending)
                        pending = b""
                if got >= size:
                    break
                self.feed()
                try:
                    body = c.recv(1024)
                    idle = 0
                except OSError:  # a slow patch on the link: wait a little before giving up
                    idle += 1
                    body = b""
                    if idle >= 3:
                        break
                    continue
                if not body:
                    break
        if got != size or _hex(h) != want:
            os.remove(tmp)
            return self.reply(c, 400, "upload damaged (%d of %d bytes)" % (got, size))
        gc.collect()
        try:  # a file that does not even compile would stop the board starting
            with open(tmp) as f:
                compile(f.read(), name, "exec")
        except MemoryError:
            pass
        except Exception as e:
            os.remove(tmp)
            return self.reply(c, 400, "will not compile: %r" % (e,))
        self.reply(c, 200, "ok %s" % name)

    def clear(self):
        for f in os.listdir():
            if f.endswith(".tmp"):
                os.remove(f)

    def apply(self, c):
        names = [f[:-4] for f in os.listdir() if f.endswith(".py.tmp")]
        if not names:
            return self.reply(c, 400, "nothing uploaded")
        for n in names:
            try:
                os.remove(n + ".bak")
            except OSError:
                pass
            if n in os.listdir():
                os.rename(n, n + ".bak")
            os.rename(n + ".tmp", n)
        with open(TRY_FILE, "w") as f:
            f.write("0")
        self.reply(c, 200, "applied %s; restarting" % " ".join(names))
        time.sleep_ms(1000)
        machine.reset()


def start(feed, show):
    """Start the server, or return None if secrets.py has no OTA_KEY."""
    try:
        from secrets import OTA_KEY
    except ImportError:
        return None
    return Server(OTA_KEY, feed, show)
