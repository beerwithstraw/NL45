"""
Validation check tests using synthetic NL45Extract fixtures.

Tests each check in isolation:
  1. STATUS_IDENTITY — pass, fail, skip (all-zero row)
  2. COMPLAINT_SUM   — pass, fail
  3. RATIO_SANITY    — warn on divergence
  4. COMPLETENESS    — fail on missing total row, warn on missing claim row
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from extractor.models import NL45Extract, NL45StatusData, NL45BenchmarkData
from validation.checks import run_validations, ValidationResult
from config.row_registry import NL45_ROW_ORDER, SUMMARY_ROW
from config.settings import STATUS_METRICS


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _make_row(opening=0, additions=0, fully=0, partial=0, rejected=0, pending=0, total_ytd=0):
    return {
        "opening_balance":      float(opening),
        "additions":            float(additions),
        "fully_accepted":       float(fully),
        "partial_accepted":     float(partial),
        "rejected":             float(rejected),
        "pending_eoq":          float(pending),
        "total_registered_ytd": float(total_ytd),
    }


def _perfect_extract():
    """Bajaj Q3 values — all checks should PASS or SKIP."""
    status = NL45StatusData()
    status.data = {
        "proposal_related":   _make_row(0,    2,   0, 0,   2,  0,    8),
        "claim":              _make_row(6,  789, 178, 0, 615,  2, 2075),
        "policy_related":     _make_row(0,  345, 223, 0, 121,  1,  787),
        "premium":            _make_row(0,   46,   5, 0,  41,  0,  151),
        "refund":             _make_row(0,   44,  23, 0,  20,  1,   98),
        "coverage":           _make_row(0,    1,   0, 0,   1,  0,    9),
        "cover_note_related": _make_row(0,    0,   0, 0,   0,  0,    0),
        "product":            _make_row(0,    6,   3, 0,   3,  0,   10),
        "others":             _make_row(0,  124,  50, 0,  74,  0,  240),
        "total_complaints":   _make_row(6, 1357, 482, 0, 877,  4, 3380),
    }
    bm = NL45BenchmarkData(
        policies_prev_year=35549831,
        claims_prev_year=4440689,
        policies_curr_year=27474096,
        claims_curr_year=4385293,
        policy_complaints_per_10k=0.47,
        claim_complaints_per_10k=4.73,
    )
    return NL45Extract(
        source_file="test.pdf",
        company_key="bajaj_allianz",
        company_name="Test Co",
        quarter="Q3",
        year="202526",
        status_data=status,
        benchmark_data=bm,
    )


def _statuses(results, check_prefix):
    return [r.status for r in results if r.check_name.startswith(check_prefix)]


# ── 1. STATUS_IDENTITY ────────────────────────────────────────────────────────

def test_status_identity_passes_for_perfect_data():
    exc = _perfect_extract()
    results = run_validations([exc])
    identity_results = [r for r in results if r.check_name == "STATUS_IDENTITY"]
    fails = [r for r in identity_results if r.status == "FAIL"]
    assert not fails, f"Unexpected FAIL: {fails}"
    # Non-zero rows must PASS; all-zero row (cover_note_related) must SKIP
    passes = [r for r in identity_results if r.status == "PASS"]
    skips  = [r for r in identity_results if r.status == "SKIP"]
    assert len(passes) >= 9
    assert any(r.complaint_type == "cover_note_related" for r in skips)


def test_status_identity_fails_on_broken_row():
    exc = _perfect_extract()
    # Break claim row: opening=6, additions=789, but resolved only 100 (short by ~693)
    exc.status_data.data["claim"] = _make_row(6, 789, 100, 0, 0, 2, 2075)
    results = run_validations([exc])
    identity_fails = [r for r in results
                      if r.check_name == "STATUS_IDENTITY"
                      and r.complaint_type == "claim"
                      and r.status == "FAIL"]
    assert identity_fails, "Expected STATUS_IDENTITY FAIL for broken claim row"


def test_status_identity_skips_all_zero_row():
    exc = _perfect_extract()
    results = run_validations([exc])
    skip = next((r for r in results
                 if r.check_name == "STATUS_IDENTITY"
                 and r.complaint_type == "cover_note_related"), None)
    assert skip is not None and skip.status == "SKIP"


# ── 2. COMPLAINT_SUM ─────────────────────────────────────────────────────────

def test_complaint_sum_passes_for_perfect_data():
    exc = _perfect_extract()
    results = run_validations([exc])
    sum_fails = [r for r in results
                 if r.check_name.startswith("COMPLAINT_SUM") and r.status == "FAIL"]
    assert not sum_fails, f"Unexpected COMPLAINT_SUM FAIL: {sum_fails}"


def test_complaint_sum_fails_on_wrong_total():
    exc = _perfect_extract()
    # Artificially inflate total additions to mismatch
    exc.status_data.data["total_complaints"]["additions"] = 9999.0
    results = run_validations([exc])
    sum_fail = next((r for r in results
                     if r.check_name == "COMPLAINT_SUM_ADDITIONS" and r.status == "FAIL"), None)
    assert sum_fail is not None, "Expected COMPLAINT_SUM_ADDITIONS FAIL"


# ── 3. RATIO_SANITY ──────────────────────────────────────────────────────────

def test_ratio_sanity_warns_on_large_divergence():
    exc = _perfect_extract()
    # Replace ratio with a wildly wrong value
    exc.benchmark_data.policy_complaints_per_10k = 999.0
    results = run_validations([exc])
    ratio_warn = next((r for r in results
                       if r.check_name == "RATIO_SANITY_POLICY" and r.status == "WARN"), None)
    assert ratio_warn is not None, "Expected RATIO_SANITY_POLICY WARN"


def test_ratio_sanity_skips_when_benchmark_missing():
    exc = _perfect_extract()
    exc.benchmark_data = None
    results = run_validations([exc])
    ratio_results = [r for r in results if r.check_name.startswith("RATIO_SANITY")]
    assert not ratio_results, "Expected no ratio checks when benchmark_data is None"


# ── 4. COMPLETENESS ──────────────────────────────────────────────────────────

def test_completeness_passes_for_perfect_data():
    exc = _perfect_extract()
    results = run_validations([exc])
    comp_fails = [r for r in results
                  if r.check_name == "COMPLETENESS" and r.status == "FAIL"]
    assert not comp_fails, f"Unexpected COMPLETENESS FAIL: {comp_fails}"


def test_completeness_fails_when_status_data_empty():
    exc = _perfect_extract()
    exc.status_data = NL45StatusData()  # empty
    results = run_validations([exc])
    comp_fail = next((r for r in results
                      if r.check_name == "COMPLETENESS" and r.status == "FAIL"), None)
    assert comp_fail is not None, "Expected COMPLETENESS FAIL for empty status_data"


def test_completeness_fails_when_total_row_missing():
    exc = _perfect_extract()
    del exc.status_data.data["total_complaints"]
    results = run_validations([exc])
    comp_fail = next((r for r in results
                      if r.check_name == "COMPLETENESS"
                      and r.complaint_type == "total_complaints"
                      and r.status == "FAIL"), None)
    assert comp_fail is not None, "Expected COMPLETENESS FAIL for missing total row"


def test_completeness_warns_when_claim_row_missing():
    exc = _perfect_extract()
    del exc.status_data.data["claim"]
    results = run_validations([exc])
    comp_warn = next((r for r in results
                      if r.check_name == "COMPLETENESS"
                      and r.complaint_type == "claim"
                      and r.status == "WARN"), None)
    assert comp_warn is not None, "Expected COMPLETENESS WARN for missing claim row"
