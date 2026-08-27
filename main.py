#!/usr/bin/env python3
"""Walid AI Desktop v10.1 — Production entrypoint (thin launcher)."""
import sys
from ui.app import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
