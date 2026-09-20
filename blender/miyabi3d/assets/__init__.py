"""お品書きの一品ずつを組み立てるモジュール群.

各モジュールは build(collection=None) -> dict を持ち、
{"name", "objects", "focus", "radius"} を返す。
"""

from __future__ import annotations

import importlib

MODULES = ("wanmono", "sushi", "donabe", "shuki", "chochin", "emblem",
           "hashi", "zen")


def get(name: str):
    return importlib.import_module(f"{__name__}.{name}")


def build(name: str, **kwargs) -> dict:
    return get(name).build(**kwargs)
