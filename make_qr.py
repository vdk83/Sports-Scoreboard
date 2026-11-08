#!/usr/bin/env python3
"""Make a QR code for the board's settings page, to print or show on a screen.

    pip3 install segno                 # once
    python3 make_qr.py 192.168.1.50       # or no address: uses the one deploy.py remembers

Writes settings_qr.png. The code holds the board's address and the OTA key (.ota_key), so anyone who
scans it can change the settings and also send new code to the board: keep the printout private.
Make it again if the router gives the board a new address.
"""
import os
import struct
import sys
import zlib

import segno

HERE = os.path.dirname(os.path.abspath(__file__))


def png(rows, scale, border, path):
    n = len(rows)
    size = (n + 2 * border) * scale
    raw = b""
    for y in range(size):
        r = y // scale - border
        line = bytearray()
        for x in range(size):
            c = x // scale - border
            dark = 0 <= r < n and 0 <= c < n and rows[r][c]
            line.append(0 if dark else 255)
        raw += b"\0" + bytes(line)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def main():
    saved = os.path.join(HERE, ".ota_host")
    host = sys.argv[1] if len(sys.argv) > 1 else open(saved).read().strip()
    key = open(os.path.join(HERE, ".ota_key")).read().strip()
    url = "http://%s:8080/ui?k=%s" % (host, key)  # the settings page (ota.py + app.py)
    q = segno.make(url, error="m", micro=False)
    rows = [[bool(v) for v in row] for row in q.matrix]
    png(rows, 12, 4, os.path.join(HERE, "settings_qr.png"))
    print("http://%s:8080/ui?k=...  (%dx%d modules) -> settings_qr.png" % (host, len(rows), len(rows)))


main()
