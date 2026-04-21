"""
Tests for config/row_registry.py

Verifies:
  - Every alias resolves to a key that exists in NL45_ROW_ORDER
  - No alias maps to a non-existent key
  - normalise_text → alias → key round-trips for all observed Bajaj PDF labels
  - should_skip() fires correctly for header/footnote rows
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from config.row_registry import (
    NL45_ROW_ORDER, NL45_ROW_ALIASES, NL45_ROW_DISPLAY_NAMES,
    resolve_row, should_skip,
)
from extractor.normaliser import normalise_text


# ── Alias integrity ───────────────────────────────────────────────────────────

def test_every_alias_resolves_to_known_key():
    for alias, key in NL45_ROW_ALIASES.items():
        assert key in NL45_ROW_ORDER, (
            f"Alias '{alias}' → '{key}' but '{key}' is not in NL45_ROW_ORDER"
        )


def test_display_names_cover_all_row_keys():
    for key in NL45_ROW_ORDER:
        assert key in NL45_ROW_DISPLAY_NAMES, (
            f"'{key}' has no entry in NL45_ROW_DISPLAY_NAMES"
        )


# ── Round-trip: exact PDF labels from Bajaj sample ───────────────────────────

@pytest.mark.parametrize("pdf_label, expected_key", [
    ("Proposal Related",                           "proposal_related"),
    ("Claim",                                      "claim"),
    ("Policy Related",                             "policy_related"),
    ("Premium",                                    "premium"),
    ("Refund",                                     "refund"),
    ("Coverage",                                   "coverage"),
    ("Cover Note Related",                         "cover_note_related"),
    ("Product",                                    "product"),
    ("Others (to be specified)\n(i)_________\n(ii) _________", "others"),
    ("Total Number",                               "total_complaints"),
])
def test_pdf_label_round_trip(pdf_label, expected_key):
    resolved = resolve_row(pdf_label, normalise_text)
    assert resolved == expected_key, (
        f"PDF label '{pdf_label[:40]}' → '{resolved}', expected '{expected_key}'"
    )


# ── resolve_row: case / whitespace robustness ─────────────────────────────────

@pytest.mark.parametrize("raw, expected_key", [
    ("CLAIM",            "claim"),
    ("  Policy Related ", "policy_related"),
    ("cover note related", "cover_note_related"),
    ("Others",            "others"),
    ("total number",      "total_complaints"),
    ("TOTAL",             "total_complaints"),
])
def test_resolve_row_normalisation(raw, expected_key):
    assert resolve_row(raw, normalise_text) == expected_key


def test_resolve_row_unknown_returns_none():
    assert resolve_row("Completely Unknown Label XYZ", normalise_text) is None


def test_resolve_row_empty_returns_none():
    assert resolve_row("", normalise_text) is None


# ── should_skip: header and footnote detection ────────────────────────────────

@pytest.mark.parametrize("label", [
    "FORM NL-45 GREIVANCE DISPOSAL",
    "Complaints made by customers",
    "Complaints Resolved",
    "Opening Balance *",
    "Additions during the quarter (net of duplicate complaints)",
    "Note :- From the overall complaint of 1357",
    "(a) Opening balance should tally with the closing balance",
    "(e) For 1 to 7 Similar break-up",
])
def test_should_skip_headers_and_footnotes(label):
    assert should_skip(label), f"Expected should_skip=True for: '{label[:60]}'"


@pytest.mark.parametrize("label", [
    "Claim",
    "Policy Related",
    "Total Number",
    "Others (to be specified)",
])
def test_should_not_skip_data_rows(label):
    assert not should_skip(label), f"Expected should_skip=False for: '{label}'"
