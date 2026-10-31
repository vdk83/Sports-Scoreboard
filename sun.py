# Sunrise and sunset (NOAA's "almanac" method, good to a minute or two).
import math

ZENITH = 90.833  # the sun's upper edge on the horizon, with refraction


def _day_of_year(year, month, day):
    cum = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    n = cum[month - 1] + day
    if month > 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        n += 1
    return n


def _event(lat, lon, n, rising):
    """UTC hour (0..24) of sunrise or sunset on day-of-year n, or None (polar day/night)."""
    rad = math.pi / 180
    lng_hour = lon / 15
    t = n + ((6 if rising else 18) - lng_hour) / 24
    m = 0.9856 * t - 3.289
    l = (m + 1.916 * math.sin(m * rad) + 0.020 * math.sin(2 * m * rad) + 282.634) % 360
    ra = math.atan(0.91764 * math.tan(l * rad)) / rad % 360
    ra += math.floor(l / 90) * 90 - math.floor(ra / 90) * 90
    ra /= 15
    sin_dec = 0.39782 * math.sin(l * rad)
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = (math.cos(ZENITH * rad) - sin_dec * math.sin(lat * rad)) / (cos_dec * math.cos(lat * rad))
    if cos_h > 1 or cos_h < -1:
        return None
    h = (360 - math.acos(cos_h) / rad if rising else math.acos(cos_h) / rad) / 15
    return (h + ra - 0.06571 * t - 6.622 - lng_hour) % 24


def times(lat, lon, year, month, day):
    """(sunrise, sunset) as UTC hours since midnight of that UTC date; either may be None."""
    n = _day_of_year(year, month, day)
    return _event(lat, lon, n, True), _event(lat, lon, n, False)
