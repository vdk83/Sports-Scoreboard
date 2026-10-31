# Interstate 75 sports scoreboard

Dodgers (MLB), Seahawks (NFL) and Kraken (NHL) scores on a 64x32 HUB75 panel,
using a Pimoroni Interstate 75 W (RP2350) running Pimoroni MicroPython v0.0.5.

| File | Purpose |
| --- | --- |
| `main.py` | Tiny launcher that starts `app.py` and undoes a bad WiFi update. Install over USB; never sent over WiFi |
| `app.py` | The scoreboard itself: WiFi, clock sync, polling, display loop |
| `ota.py` | Update-over-WiFi server on the board (port 8080); also serves the settings page and log |
| `settings.py` | Settings (`config.json`), the log ring buffer and the flash cache. Also runs on the computer |
| `sun.py` | Sunrise and sunset for the idle screen |
| `deploy.py` | Run on the computer: sends changed files to the board over WiFi |
| `espn.py` | Football and hockey: streams ESPN's scoreboard JSON and extracts only our games |
| `mlb.py` | Baseball: MLB Stats API (runners, outs, count, ABS challenges remaining) |
| `scores.py` | Team config, which games to show, status text, score-change wording |
| `board.py` | 3x5 font, layouts (1-4 games), score animations |
| `critters.py` | Idle-screen cameos: seasonal, holiday and team (see below) |
| `jokes.py` | Jokes that scroll on the ticker |
| `weather.py` | Current weather for the clock slide (Open-Meteo, no key) |
| `cameo_demo.py` | Looping slideshow of every seasonal cameo |
| `preview.py` | Run on the computer: PNGs or a live window of cameos, layouts and the clock, no board needed |
| `test_logic.py`, `test_app.py` | Run on the computer: `python3 -m unittest test_logic test_app` (`test_app` runs `app.py` with the board's hardware faked) |
| `demo.py` | Plays each animation and every cameo on the panel without a live game |
| `secrets.py` | WiFi login. Lives on the board only (see `secrets.example.py`) |

Deploy over WiFi: `python3 deploy.py 192.168.1.50` (the address shows on the panel while it starts up;
it is remembered after that). Only changed files are sent, then the board restarts. The key is in
`.ota_key` here and `OTA_KEY` in `secrets.py` on the board. If new code cannot start three times in a
row, the board puts the old files back by itself (kept as `*.py.bak`). First install, or after changing
`main.py`, still needs USB: `mpremote cp main.py app.py ota.py espn.py mlb.py board.py critters.py jokes.py weather.py scores.py settings.py sun.py :` then `mpremote reset`.

Developing without the board: `python3 preview.py cameos|games|clock` writes pictures to `preview/`, and
`python3 preview.py cameo Pumpkin` plays one live in a window.

Games appear 14 h before the start and stay 12 h after. One game fills the
panel, two split it in half, three or four stack in rows. Times are Pacific
(change `UTC_STANDARD_OFFSET` in `scores.py`).

Live baseball shows the diamond (bases turn yellow when occupied), three out dots,
and two ABS challenge squares per team (filled = challenge still available) when one
or two games are on screen; with three or more games it falls back to one line each.

## Idle screen

With no games on, the top shows a rotating slide (clock with date and weather, then each
team's next game with its record and streak; "IN 23 MIN" in the last hour before a start; rival opponents
in gold; then the next sunrise or sunset). The bottom scrolls the league scores followed by a joke. Weather and
sun are for the default location and times are Pacific; change both on the settings page.

Every 2-5 minutes (adjustable) a cameo takes over the whole panel for a few seconds. Never the same twice in a row. 40% of the time on a holiday it is the holiday's,
a quarter of the time it is one of our teams, otherwise it is a seasonal one (Pacific local date):

| Kind | Cameos |
| --- | --- |
| Winter | snowman strolling by, snowman losing his head, penguin belly-slide |
| Spring | rain and sprouting flowers, butterfly fluttering over a flower |
| Summer | sun putting on sunglasses, ice cream scoop splat, fireflies, bouncing beach ball |
| Fall | jack-o'-lantern hopping, falling leaves, ghost and bat (October only), turkey (November only) |
| Holidays | fireworks (Jul 3-5), Christmas tree (Dec 14-26), heart (Feb 13-14), shamrock (Mar 16-17) |
| Teams | hawk flying by, the 12 flag, Kraken tentacles and eye, Dodgers baseball |

## Settings page and diagnostics

Open `http://<board address>:8080/ui?k=<the key in .ota_key>` on a phone or computer on the same WiFi
(the board's address shows on the panel at startup). It sets the idle mode (NORMAL/CLOCK/ART), brightness
(auto or fixed), how often cameos play (often/normal/rare/off), plays a cameo now, and sets latitude,
longitude and time zone. Choices are kept in `config.json` on the board and survive restarts; button B's mode
choice is saved too. `/log?k=...` shows recent log lines, including the ones from before the last crash or
automatic restart. The key travels in the address, so keep this to your home network.

A single pixel in the top right corner means trouble: red = no WiFi, amber = a data source has failed several
times in a row.

Other behaviour:
- **Rivalries.** Games against a rival (`rivals` in `scores.py`) are tagged RIV. A shutout win says SHUTOUT!.
- **After a restart** the idle screen is filled from a cache in flash (written every 30 minutes, ignored if older than 6 hours) until fresh data arrives.
- **Second WiFi network.** Add `WIFI_SSID2` and `WIFI_PASSWORD2` to `secrets.py` (see `secrets.example.py`); it is tried when the first fails. Retries back off up to a minute.
- **No stalls.** One loop runs everything; every wait on the network draws the next frame and feeds the watchdog, so the ticker and animations keep moving. (A second core for downloads was tried and made the display pause.)
- **Night mode.** The panel dims after 7 pm and a lot after 10 pm; daytime cameos get a sky colour behind them.
- **Game over.** Confetti and WIN! or grey rain and LOSS when one of our games ends.
- **Buttons.** A plays a cameo now. B cycles NORMAL, CLOCK (big clock + ticker) and ART (cameos nonstop).
