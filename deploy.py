#!/usr/bin/env python3
"""Send changed code to the scoreboard over WiFi.

    python3 deploy.py 192.168.1.50  # the address shown on the panel at startup (remembered afterwards)
    python3 deploy.py            # the address used last time

The key is in the file .ota_key next to this script (the same OTA_KEY as in secrets.py on the board).
"""
import hashlib
import http.client
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["espn.py", "mlb.py", "board.py", "critters.py", "jokes.py", "weather.py", "scores.py", "ota.py",
         "settings.py", "sun.py", "app.py", "demo.py", "cameo_demo.py"]
PORT = 8080


def call(host, key, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection(host, PORT, timeout=15)
    h = {"X-Key": key}
    h.update(headers or {})
    conn.request(method, path, body=body, headers=h)
    r = conn.getresponse()
    text = r.read().decode(errors="replace")
    conn.close()
    return r.status, text


def main():
    saved = os.path.join(HERE, ".ota_host")  # the address that worked last time
    host = sys.argv[1] if len(sys.argv) > 1 else open(saved).read().strip() if os.path.exists(saved) else "scoreboard.local"
    key = open(os.path.join(HERE, ".ota_key")).read().strip()
    status, text = call(host, key, "GET", "/hashes")
    if status != 200:
        sys.exit("board said %d: %s" % (status, text))
    open(saved, "w").write(host)
    on_board = dict(line.split() for line in text.splitlines())
    todo = []
    for name in FILES:
        data = open(os.path.join(HERE, name), "rb").read()
        digest = hashlib.sha256(data).hexdigest()
        if on_board.get(name) != digest:
            todo.append((name, data, digest))
    if not todo:
        print("board is up to date")
        return
    call(host, key, "POST", "/clear")
    for name, data, digest in todo:
        for attempt in range(3):  # the board's WiFi link is slow now and then
            try:
                status, text = call(host, key, "PUT", "/f/" + name, data, {"X-Sha256": digest})
            except OSError as e:
                status, text = 0, repr(e)
            if status == 200:
                break
            time.sleep(2)
        print("%-14s %s" % (name, "sent" if status == 200 else "FAILED: %s" % text))
        if status != 200:
            call(host, key, "POST", "/clear")
            sys.exit("nothing was applied")
    try:
        print(call(host, key, "POST", "/apply")[1])
    except OSError:  # the board restarts right after answering, so the answer can get lost
        print("applied; the board is restarting")
    for _ in range(30):  # wait for the board to come back
        time.sleep(2)
        try:
            print("back up:", call(host, key, "GET", "/status")[1].strip())
            return
        except OSError:
            pass
    print("the board has not answered yet; if the panel shows the scoreboard it is fine")


main()
