# Interstate 75 sports scoreboard

Dodgers (MLB), Seahawks (NFL) and Kraken (NHL) scores on a 64x32 HUB75 panel,
using a Pimoroni Interstate 75 W (RP2350) running Pimoroni MicroPython v0.0.5.

| File | Purpose |
| --- | --- |
| `main.py` | Tiny launcher that starts `app.py` and undoes a bad WiFi update. Install over USB; never sent over WiFi |
| `app.py` | The scoreboard itself: WiFi, clock sync, polling, display loop |
| `ota.py` | Update-over-WiFi server on the board (port 8080) |
| `deploy.py` | Run on the computer: sends changed files to the board over WiFi |
| `espn.py` | Football and hockey: streams ESPN's scoreboard JSON and extracts only our games |
| `mlb.py` | Baseball: MLB Stats API (runners, outs, count, ABS challenges remaining) |
| `scores.py` | Team config, which games to show, status text, score-change wording |
| `board.py` | 3x5 font, layouts (1-4 games), score animations |
| `critters.py` | Idle-screen cameos: seasonal, holiday and team (see below) |
| `jokes.py` | Jokes that scroll on the ticker |
| `weather.py` | Current weather for the clock slide (Open-Meteo, no key) |
| `cameo_demo.py` | Looping slideshow of every seasonal cameo |
| `demo.py` | Plays each animation and every cameo on the panel without a live game |
| `secrets.py` | WiFi login. Lives on the board only (see `secrets.example.py`) |

Deploy over WiFi: `python3 deploy.py 192.168.1.50` (the address shows on the panel while it starts up;
it is remembered after that). Only changed files are sent, then the board restarts. The key is in
`.ota_key` here and `OTA_KEY` in `secrets.py` on the board. If new code cannot start three times in a
row, the board puts the old files back by itself (kept as `*.py.bak`). First install, or after changing
`main.py`, still needs USB: `mpremote cp main.py app.py ota.py espn.py mlb.py board.py critters.py jokes.py weather.py scores.py :` then `mpremote reset`.

Games appear 14 h before the start and stay 12 h after. One game fills the
panel, two split it in half, three or four stack in rows. Times are Pacific
(change `UTC_STANDARD_OFFSET` in `scores.py`).

Live baseball shows the diamond (bases turn yellow when occupied), three out dots,
and two ABS challenge squares per team (filled = challenge still available) when one
or two games are on screen; with three or more games it falls back to one line each.

## Idle screen

With no games on, the top shows a rotating slide (clock with date and weather, then each
team's next game; "IN 23 MIN" in the last hour before a start). The bottom scrolls the
league scores followed by a joke. The weather is for the default location (`LATITUDE`/`LONGITUDE` in `scores.py`); times are Pacific.

Every 2-5 minutes a cameo takes over the whole panel for a few seconds (`CAMEO_MIN`/`CAMEO_MAX`
in `main.py`). Never the same twice in a row. 40% of the time on a holiday it is the holiday's,
a quarter of the time it is one of our teams, otherwise it is a seasonal one (Pacific local date):

| Kind | Cameos |
| --- | --- |
| Winter | snowman strolling by, snowman losing his head, penguin belly-slide |
| Spring | rain and sprouting flowers, butterfly fluttering over a flower |
| Summer | sun putting on sunglasses, ice cream scoop splat, fireflies, bouncing beach ball |
| Fall | jack-o'-lantern hopping, falling leaves, ghost and bat (October only), turkey (November only) |
| Holidays | fireworks (Jul 3-5), Christmas tree (Dec 14-26), heart (Feb 13-14), shamrock (Mar 16-17) |
| Teams | hawk flying by, the 12 flag, Kraken tentacles and eye, Dodgers baseball |

Other behaviour:
- **No stalls.** All downloads run on the Pico's second core; the ticker and animations keep moving.
- **Night mode.** The panel dims after 7 pm and a lot after 10 pm; daytime cameos get a sky colour behind them.
- **Game over.** Confetti and WIN! or grey rain and LOSS when one of our games ends.
- **Buttons.** A plays a cameo now. B cycles NORMAL, CLOCK (big clock + ticker) and ART (cameos nonstop).
