"""Smoke test: utility functions."""
from core.utils import safe_filename, truncate, sanitize_path


def test_safe_filename_normal():
    assert safe_filename("hello.txt") == "hello.txt"


def test_safe_filename_arabic():
    assert safe_filename("ملف.txt") == "ملف.txt"


def test_safe_filename_empty():
    assert len(safe_filename("")) > 0


def test_truncate_short():
    assert truncate("hello", 100) == "hello"


def test_truncate_long():
    result = truncate("x" * 200, 50)
    assert len(result) > 50
    assert "مقتطع" in result


def test_sanitize_path():
    from pathlib import Path
    p = sanitize_path(".")
    assert isinstance(p, Path)
    assert p.is_absolute()
