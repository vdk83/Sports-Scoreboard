# Starts the scoreboard (app.py). Never replaced over WiFi, so it can undo a bad update:
# after an update ota.py leaves a marker file (ota_try); if the new code cannot start three
# times in a row, the previous version of every updated file (*.py.bak) is put back.
import os

try:
    with open("ota_try") as f:
        tries = int(f.read())
except (OSError, ValueError):
    tries = -1

if tries >= 3:
    for name in os.listdir():
        if name.endswith(".py.bak"):
            try:
                os.remove(name[:-4])
            except OSError:
                pass
            os.rename(name, name[:-4])
    os.remove("ota_try")
    print("update rolled back")
elif tries >= 0:
    with open("ota_try", "w") as f:
        f.write(str(tries + 1))
    import machine
    machine.WDT(timeout=8000)  # code that crashes at start never feeds it, so the board restarts

import app  # runs the scoreboard
