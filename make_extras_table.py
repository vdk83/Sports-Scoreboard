#!/usr/bin/env python3
"""Rewrite the EXTRAS table in critters.py from the extras_*.py files (run after adding a cameo).

    python3 make_extras_table.py
"""
import importlib
import inspect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import critters  # noqa: E402

MODULES = ("extras_space", "extras_fun", "extras_sports", "extras_winter", "extras_winter2", "extras_spring", "extras_summer", "extras_summer2", "extras_fall", "extras_fall2", "extras_arcade")


def main():
    lines = []
    for name in MODULES:
        mod = importlib.import_module(name)
        for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ != name or not issubclass(cls, critters.Cameo):
                continue
            lines.append("    %r: (%r, %r, %r, %r)," % (cls_name, name, getattr(cls, "seasons", None), cls.months, cls.dates))
    src = open(os.path.join(HERE, "critters.py")).read()
    start = src.index("EXTRAS = {\n") + len("EXTRAS = {\n")
    end = src.index("\n}\n", start)
    open(os.path.join(HERE, "critters.py"), "w").write(src[:start] + "\n".join(lines) + src[end:])
    print(len(lines), "extra cameos in the table")


main()
