"""
Parser integration test against the Bajaj General Q3 FY2025-26 PDF.

All expected values are read directly from the PDF (verified by eye):
  TABLE 1 — complaint status grid
  TABLE 2 — benchmark/ratio metrics
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import BAJAJ_PDF
from extractor.parser import parse_pdf


@pytest.fixture(scope="module")
def bajaj_extract():
    if not os.path.exists(BAJAJ_PDF):
        pytest.skip(f"Bajaj PDF not found: {BAJAJ_PDF}")
    return parse_pdf(BAJAJ_PDF, "bajaj_allianz", quarter="Q3", year="202526")


# ── Basic extraction success ──────────────────────────────────────────────────

def test_extract_has_no_errors(bajaj_extract):
    assert not bajaj_extract.extraction_errors, bajaj_extract.extraction_errors

def test_extract_status_data_present(bajaj_extract):
    assert bajaj_extract.status_data is not None
    assert len(bajaj_extract.status_data.data) == 10  # 9 types + total

def test_extract_benchmark_data_present(bajaj_extract):
    assert bajaj_extract.benchmark_data is not None

def test_form_type(bajaj_extract):
    assert bajaj_extract.form_type == "NL45"

def test_quarter_year(bajaj_extract):
    assert bajaj_extract.quarter == "Q3"
    assert bajaj_extract.year == "202526"


# ── Status table: spot checks for every complaint type ───────────────────────

@pytest.mark.parametrize("complaint_type, opening, additions, fully, partial, rejected, pending, total_ytd", [
    ("proposal_related",  0,    2,    0,   0,    2,   0,    8),
    ("claim",             6,  789,  178,   0,  615,   2, 2075),
    ("policy_related",    0,  345,  223,   0,  121,   1,  787),
    ("premium",           0,   46,    5,   0,   41,   0,  151),
    ("refund",            0,   44,   23,   0,   20,   1,   98),
    ("coverage",          0,    1,    0,   0,    1,   0,    9),
    ("cover_note_related",0,    0,    0,   0,    0,   0,    0),
    ("product",           0,    6,    3,   0,    3,   0,   10),
    ("others",            0,  124,   50,   0,   74,   0,  240),
    ("total_complaints",  6, 1357,  482,   0,  877,   4, 3380),
])
def test_status_row_values(bajaj_extract, complaint_type, opening, additions,
                           fully, partial, rejected, pending, total_ytd):
    m = bajaj_extract.status_data.data.get(complaint_type)
    assert m is not None, f"Row '{complaint_type}' not extracted"

    def _v(key, expected):
        val = m.get(key)
        # Treat None as 0 when expected is 0 (dash in PDF = None = 0)
        actual = val if val is not None else 0.0
        assert actual == pytest.approx(float(expected)), (
            f"{complaint_type}.{key}: got {val}, expected {expected}"
        )

    _v("opening_balance",      opening)
    _v("additions",            additions)
    _v("fully_accepted",       fully)
    _v("partial_accepted",     partial)
    _v("rejected",             rejected)
    _v("pending_eoq",          pending)
    _v("total_registered_ytd", total_ytd)


# ── Status identity check (Opening + Additions = Resolved + Pending) ──────────

@pytest.mark.parametrize("complaint_type", [
    "proposal_related", "claim", "policy_related", "premium",
    "refund", "coverage", "product", "others", "total_complaints",
])
def test_status_identity_holds(bajaj_extract, complaint_type):
    m = bajaj_extract.status_data.data.get(complaint_type, {})
    opening  = m.get("opening_balance") or 0.0
    additions = m.get("additions") or 0.0
    fully    = m.get("fully_accepted") or 0.0
    partial  = m.get("partial_accepted") or 0.0
    rejected = m.get("rejected") or 0.0
    pending  = m.get("pending_eoq") or 0.0
    assert abs((opening + additions) - (fully + partial + rejected + pending)) <= 2.0, (
        f"Identity failed for '{complaint_type}': "
        f"LHS={opening + additions}, RHS={fully + partial + rejected + pending}"
    )


# ── Benchmark table values ────────────────────────────────────────────────────

def test_benchmark_policies_prev_year(bajaj_extract):
    assert bajaj_extract.benchmark_data.policies_prev_year == pytest.approx(35549831.0)

def test_benchmark_claims_prev_year(bajaj_extract):
    assert bajaj_extract.benchmark_data.claims_prev_year == pytest.approx(4440689.0)

def test_benchmark_policies_curr_year(bajaj_extract):
    assert bajaj_extract.benchmark_data.policies_curr_year == pytest.approx(27474096.0)

def test_benchmark_claims_curr_year(bajaj_extract):
    assert bajaj_extract.benchmark_data.claims_curr_year == pytest.approx(4385293.0)

def test_benchmark_policy_ratio(bajaj_extract):
    assert bajaj_extract.benchmark_data.policy_complaints_per_10k == pytest.approx(0.47)

def test_benchmark_claim_ratio(bajaj_extract):
    assert bajaj_extract.benchmark_data.claim_complaints_per_10k == pytest.approx(4.73)
