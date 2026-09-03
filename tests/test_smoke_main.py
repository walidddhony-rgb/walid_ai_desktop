"""Smoke test: main module imports."""

import importlib


def test_main_imports():
    mod = importlib.import_module("main")
    assert mod is not None
