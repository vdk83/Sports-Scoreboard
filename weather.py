# Current weather from Open-Meteo (free, no key). Set LATITUDE/LONGITUDE in scores.py.
import json

import espn

HOST = "api.open-meteo.com"
PATH = ("/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,weather_code"
        "&temperature_unit=fahrenheit")


def kind_for(code):
    if code <= 1:
        return "sun"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (45, 48):
        return "fog"
    if code >= 95:
        return "storm"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    return "cloud"


def fetch(lat, lon):
    """(icon kind, '54F') for the current conditions."""
    s, body = espn._open(HOST, PATH % (lat, lon))
    try:
        while len(body) < 3000:
            d = s.read(512)
            if not d:
                break
            body += d
    finally:
        s.close()
    cur = json.loads(body)["current"]
    return kind_for(int(cur["weather_code"])), "%dF" % round(cur["temperature_2m"])
