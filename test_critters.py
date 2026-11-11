"""Tests for the cameos, including the extra ones that live in extras_*.py.

    python3 -m unittest test_critters
"""
import gc
import importlib
import inspect
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
gc.mem_free = lambda: 200000  # MicroPython only

import board  # noqa: E402
import critters  # noqa: E402


class Counting:
    """The bit of PicoGraphics that Board uses, counting rectangles."""

    def __init__(self):
        self.rects = 0

    def create_pen(self, r, g, b):
        assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255, (r, g, b)
        return (r, g, b)

    def set_pen(self, p):
        pass

    def rectangle(self, x, y, w, h):
        self.rects += 1
        assert 0 <= x and 0 <= y and x + w <= 64 and y + h <= 32 and w > 0 and h > 0, (x, y, w, h)  # Board clips


MODULES = ("extras_space", "extras_fun", "extras_sports", "extras_winter", "extras_winter2", "extras_spring", "extras_summer", "extras_summer2", "extras_fall", "extras_fall2", "extras_arcade", "extras_games")


def extra_classes():
    out = []
    for name in MODULES:
        mod = importlib.import_module(name)
        for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ == name and issubclass(cls, critters.Cameo):
                out.append(cls)
    return out


class CameoTest(unittest.TestCase):
    def test_table_matches_the_files(self):
        found = {c.__name__: c for c in extra_classes()}
        self.assertEqual(sorted(found), sorted(critters.EXTRAS), "run make_extras_table.py")
        for name, (module, seasons, months, dates) in critters.EXTRAS.items():
            cls = found[name]
            self.assertEqual((cls.__module__, getattr(cls, "seasons", None), cls.months, cls.dates),
                             (module, seasons, months, dates), name)

    def test_every_extra_cameo_draws_all_its_frames(self):
        for cls in extra_classes():
            g = Counting()
            b = board.Board(g, 64, 32)
            c = cls()
            worst = 0
            while not c.done:
                before = g.rects
                c.draw(b, (0, 18, 45))
                worst = max(worst, g.rects - before)
            self.assertGreater(c.total, 60, cls.__name__)
            self.assertLess(worst, 700, "%s draws %d rectangles in one frame" % (cls.__name__, worst))

    def test_every_cameo_in_the_original_file_still_draws(self):
        for pool in list(critters.CAMEOS.values()) + [critters.HOLIDAYS, critters.TEAMS]:
            for cls in pool:
                c = cls()
                b = board.Board(Counting(), 64, 32)
                while not c.done:
                    c.draw(b)

    def test_pick_loads_extras_and_release_frees_them(self):
        seen = set()
        for _ in range(400):
            c = critters.pick(7, 4)   # July 4th: holiday cameos too
            seen.add(type(c).__name__)
            c.draw(board.Board(Counting(), 64, 32))
        self.assertTrue(seen & set(critters.EXTRAS), "no extra cameo was ever picked")
        self.assertTrue(critters._loaded)
        critters.release()
        self.assertEqual(critters._loaded, [])
        self.assertFalse(any(m in sys.modules for m in MODULES) and critters._loaded)

    def test_make_by_name(self):
        self.assertEqual(type(critters.make("Rocket")).__name__, "Rocket")
        self.assertEqual(type(critters.make("Pumpkin")).__name__, "Pumpkin")
        self.assertIsNone(critters.make("NoSuchThing"))
        critters.release()

    def test_every_month_and_day_can_pick(self):
        for month in range(1, 13):
            for day in (1, 15, 31):
                for _ in range(20):
                    critters.pick(month, day, [("football", "SEA")]).draw(board.Board(Counting(), 64, 32))

    def test_seasonal_and_holiday_rules(self):
        for _ in range(300):
            name = type(critters.pick(1, 15)).__name__     # mid January
            if name in critters.EXTRAS:
                module, seasons, months, dates = critters.EXTRAS[name]
                self.assertTrue(seasons is None or "winter" in seasons, name)
                self.assertIsNone(dates, name)             # no holiday cameo outside its dates
        seen = {type(critters.pick(12, 31)).__name__ for _ in range(400)}
        self.assertIn("NewYear", seen)

    def test_low_memory_falls_back_to_the_built_in_cameos(self):
        old = gc.mem_free
        gc.mem_free = lambda: 30000
        try:
            for _ in range(200):
                c = critters.pick(6, 1)
                self.assertNotIn(type(c).__name__, critters.EXTRAS)
        finally:
            gc.mem_free = old
        self.assertEqual(critters._loaded, [])


if __name__ == "__main__":
    unittest.main()
