# Interstate 75 sports scoreboard

Dodgers (MLB), Seahawks (NFL) and Kraken (NHL) scores, plus any NBA and MLS team (defaults: Warriors, Sounders), on a 64x32 HUB75 panel,
using a Pimoroni Interstate 75 W (RP2350) running Pimoroni MicroPython v0.0.5.

| File | Purpose |
| --- | --- |
| `main.py` | Tiny launcher that starts `app.py` and undoes a bad WiFi update. Install over USB; never sent over WiFi |
| `app.py` | The scoreboard itself: WiFi, clock sync, polling, display loop |
| `ota.py` | Update-over-WiFi server on the board (port 8080); also serves the settings page and log |
| `teams.py` | Every MLB, NFL, NHL, NBA and MLS team (names, abbreviations, colours), made by `make_teams.py` |
| `settings.py` | Settings (`config.json`), the log ring buffer and the flash cache. Also runs on the computer |
| `sun.py` | Sunrise and sunset for the idle screen |
| `make_qr.py` | Run on the computer: makes a QR code for the settings page (output `settings_qr*` holds the key; gitignored) |
| `deploy.py` | Run on the computer: sends changed files to the board over WiFi |
| `espn.py` | Football and hockey: streams ESPN's scoreboard JSON and extracts only our games |
| `news.py` | League headlines for the idle ticker (ESPN news feed, streamed, a few per followed sport every 30 min; switch off on the settings page) |
| `nhl.py` | Hockey: shots on goal and power play for live games (ESPN summary and situation) |
| `mlb.py` | Baseball: MLB Stats API (runners, outs, count, ABS challenges remaining) |
| `scores.py` | Team config, which games to show, status text, score-change wording |
| `board.py` | 3x5 font, layouts (1-4 games), score animations |
| `critters.py` | Idle-screen cameos: seasonal, holiday and team (see below) |
| `extras_any.py`, `extras_winter.py`, `extras_spring.py`, `extras_summer.py`, `extras_fall.py` | More cameos, by season (`make_extras_table.py` builds their table) |
| `jokes.py` | Jokes that scroll on the ticker |
| `weather.py` | Current weather for the clock slide (Open-Meteo, no key) |
| `cameo_demo.py` | Looping slideshow of every seasonal cameo |
| `preview.py` | Run on the computer: PNGs or a live window of cameos, layouts and the clock, no board needed |
| `test_logic.py`, `test_app.py`, `test_critters.py` | Run on the computer: `python3 -m unittest test_logic test_app test_critters` (`test_app` runs `app.py` with the board's hardware faked) |
| `demo.py` | Plays each animation and every cameo on the panel without a live game |
| `secrets.py` | WiFi login. Lives on the board only (see `secrets.example.py`) |

Deploy over WiFi: `python3 deploy.py 192.168.1.50` (the address shows on the panel while it starts up;
it is remembered after that). Only changed files are sent, then the board restarts. The key is in
`.ota_key` here and `OTA_KEY` in `secrets.py` on the board. If new code cannot start three times in a
row, the board puts the old files back by itself (kept as `*.py.bak`). First install, or after changing
`main.py`, still needs USB: `mpremote cp main.py app.py ota.py espn.py mlb.py nhl.py news.py board.py critters.py jokes.py weather.py scores.py settings.py sun.py teams.py logos.py logos_*.py page.py demo.py cameo_demo.py extras_*.py :` then `mpremote reset`.

Developing without the board: `python3 preview.py cameos|games|clock` writes pictures to `preview/`, and
`python3 preview.py cameo Pumpkin` plays one live in a window.

A followed team's game takes over the panel 1 h before the start (showing the start time) and stays
until 1 h after it ends; the rest of the time the idle screen runs. The end is the moment the board saw the game
finish, or, if it restarted since, the start plus a typical game length (`TYPICAL` in `scores.py`).
`SHOW_BEFORE` and `SHOW_AFTER` in `scores.py` change the two hours. One game fills the
panel, two split it in half, three or four stack in rows. Times follow the time zone in the settings.

What each sport shows when it is live:

| Sport | One game | Two games | Three or more |
|---|---|---|---|
| Baseball | the pitcher on the top line and the batter on the bottom line, bases, out dots, inning, count, ABS challenge squares | smaller diamond, outs, ABS squares (no names) | one line, with a tiny diamond |
| Hockey | period and clock, shots on goal and the goalie's name beside each team, red `PP` and a red edge on the team with the power play | shots as `14-21`, `PP` | one line with `PP` |
| Football | quarter and clock, four quarter squares (lit up to the current quarter), and the game's passing leader with his yards on the bottom line (`LAWRENCE 242Y`) | quarter squares | one line with the clock when it fits |
| Basketball | quarter (`OT`, `2OT`...) and clock | same | one line |
| Soccer | the minute (`67'`, `90'+3'`), `HALFTIME` | same | one line |

Shots on goal, the power play and the goalies come from `nhl.py` (extra ESPN requests per live followed game; the goalies are
found by streaming ~50 KB of the game summary, so they are looked up only every 2 minutes). The baseball names come from the MLB
feed, the passing leader from ESPN's scoreboard (it names the game's top passer, which may be the other team's QB).
The feed says a power play is on but not for whom, so the board works out the team from the next new penalty.
Basketball has no banner for each basket (they come every half minute); goals in hockey and soccer do.

## Idle screen

With no games on, the top shows a rotating slide (clock with date and weather, then each
team's next game with its record and streak; "IN 23 MIN" in the last hour before a start; rival opponents
in gold; then the next sunrise or sunset). The bottom scrolls the league scores followed by a joke. Weather and
sun are for the location in the settings (default is on the US west coast) and times are Pacific; change both on the settings page.

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
| More winter | sledding, snow angel, hot cocoa, ice skater, Santa's reindeer (Dec), fireplace, snowball fight, icicles, New Year's Eve countdown (Dec 30-31) |
| More spring | Easter bunny with eggs (Mar-Apr), frog in the rain, rainbow, bee, kite, hatching chick, ladybug |
| More summer | surfer, sandcastle and wave, watermelon seed spitting, sailboat, seagull and fries, crab, shooting stars, lemonade, palm tree and coconut, campfire |
| More fall | scarecrow and crow, squirrel and acorn, geese, apple drop, harvest moon and owl, mushrooms; October only: witch on a broom, cauldron, dancing skeleton |
| Any time | rocket launch, UFO and cow, dancing robot, cat and mouse, Pac-Man, space invaders, T. rex, spinning pizza, equalizer, home run, hockey goal, field goal, basketball, trophy, dog fetching |

The extra cameos are in `extras_*.py`, loaded only while one plays and unloaded afterwards, so they cost no memory the
rest of the time (if memory is short a built-in cameo plays instead). `critters.EXTRAS` lists them;
`make_extras_table.py` rewrites that table after you add one, and `test_critters.py` checks it. To see one on the
board: `/set?k=KEY&cameo=Rocket` (any class name); `/set?cameo=1` plays a random one. On a computer,
`python3 preview.py cameos` draws the built-in ones.

## Settings page and diagnostics

Open `http://<board address>:8080/ui?k=<the key in .ota_key>` on a phone or computer on the same WiFi
(the board's address shows on the panel at startup). It sets the idle mode (NORMAL/CLOCK/ART), brightness
(auto or fixed), how often cameos play (often/normal/rare/off), plays a cameo now, and sets latitude,
longitude and time zone. Choices are kept in `config.json` on the board and survive restarts; button B's mode
choice is saved too. `/log?k=...` shows recent log lines, including the ones from before the last crash or
automatic restart. The key travels in the address, so keep this to your home network.

**Teams you follow.** The page lists the teams followed in each sport (MLB, NFL, NHL, NBA, MLS) as buttons you tap to
remove, plus an "Add a team" drop-down with every team. Up to 4 per sport, at least 1. The board switches at once:
a sport whose teams changed forgets its old games and fetches again straight away. One score download per sport
covers all its followed teams; each followed team has its own next-game lookup and its own slide on the idle
screen. The list comes from `teams.py`, which `make_teams.py` writes from ESPN and MLB (run it again if a team
moves, then deploy). The cameos and celebrations drawn for the original Dodgers, Seahawks and Kraken only play
while those teams are followed; other teams get the plain score banner. Rivalries are only set for the originals.
In the code, `SPORTS` (3 entries) says what to download and `LEAGUES` has one entry per followed team.

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

## Reliability and settings extras

- **Backoff:** a failing data source is retried after 10 s, 20 s, 40 s... (scores, up to 2 min) or 1 min up to 15 min (the rest), not hammered.
- **Stale score:** if a live game's score has not been read for 2 minutes, the top-right status pixel turns amber.
- **Close games:** late and tight (baseball 9th+ within 1, hockey 3rd+ within 1, football 4th+ within 8) makes gold corner lights blink.
- **Brightness:** automatic mode follows the sun (full from 30 min after sunrise to 1 h before sunset, dim around it, dark-ish overnight); the settings page can switch back to clock hours.
- **Quiet hours:** the panel goes dark between two hours you pick (may wrap midnight), on the settings page.
- **Reminders:** the settings page has a Reminders section (text, date, optional time, once/daily/weekly; up to 10, 30 letters each). While the idle screen is rotating, each active reminder gets its own gold REMINDER slide after the sun slide. One with a time shows for 3 hours from then; without a time, all day. One-off reminders delete themselves once their day has passed. Kept in `reminders.json` (not in the settings backup).
- **Division standings:** for each followed baseball team the idle rotation adds its division table (two slides: ranks 1-3, then 4-5 under the division name), from the MLB standings API every 30 min. Followed teams are in their colours.
- **Countdowns:** pick "Countdown to this date" when adding a reminder; it shows "12 DAYS TO <name>" from 60 days before ("TODAY!" on the day) and removes itself afterwards.
- **Magic number and wild card:** a followed baseball team leading its division gets a "MAGIC NUMBER" slide; one chasing a wild card spot gets "WILD CARD 2" with its games behind (or ahead). They come from the same standings read, so no extra request.
- **Spoiler delay:** "Hold scores back" (15-120 s) delays every score, banner and ticker line so the panel doesn't beat your TV. After a restart the first read of each sport shows at once.
- **Timer and stopwatch:** start a countdown (any minutes, or 5/10/30) or a stopwatch (start, pause, clear) from the settings page. It takes over the top of the idle screen, "TIME'S UP!" flashes for a minute. It is not shown while games are on screen, and it is lost on restart.
- **Ticker scores:** choose all games or only your teams.
- **Clock and speed:** the settings page switches 12/24-hour time and the ticker speed (slow to faster).
- **Slide wipe:** each new idle slide wipes in from the left over about 6 frames instead of jumping.
- **Backup:** `/export?k=KEY` shows the settings as JSON; paste it into the page's Restore box after a reflash.
- **Housekeeping:** free memory goes in the log every 30 min, and the board restarts itself around 4 AM local (idle, up 6 h+).
- **CI:** GitHub Actions runs the tests on every push.

