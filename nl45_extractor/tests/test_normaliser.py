"""Tests for extractor/normaliser.py (copied unchanged from NL45)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from extractor.normaliser import clean_number, normalise_text


# ── clean_number ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    (None,          None),
    ("",            None),
    ("   ",         None),
    ("-",           None),
    ("–",           None),
    ("—",           None),
    ("n/a",         None),
    ("nil",         None),
    ("NIL",         None),
    ("0",           0.0),
    ("6",           6.0),
    ("789",         789.0),
    ("1,357",       1357.0),
    ("2,075",       2075.0),
    ("3,55,49,831", 35549831.0),   # Indian grouping — policies previous year
    ("2,74,74,096", 27474096.0),   # Indian grouping — policies current year
    ("0.47",        0.47),
    ("4.73",        4.73),
    ("(500)",       -500.0),
    ("  42  ",      42.0),
    (123,           123.0),
    (0.47,          0.47),
])
def test_clean_number(raw, expected):
    result = clean_number(raw)
    if expected is None:
        assert result is None, f"clean_number({raw!r}) → {result}, expected None"
    else:
        assert result == pytest.approx(expected), (
            f"clean_number({raw!r}) → {result}, expected {expected}"
        )


# ── normalise_text ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    (None,                    ""),
    ("",                      ""),
    ("Claim",                 "claim"),
    ("  Policy Related  ",   "policy related"),
    ("Cover Note Related",   "cover note related"),
    ("Total Number\n",       "total number"),
    ("TOTAL NUMBER",         "total number"),
    ("Others (to be specified)", "others (to be specified)"),
])
def test_normalise_text(raw, expected):
    assert normalise_text(raw) == expected
