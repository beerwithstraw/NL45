"""
Validation Checks for NL-45 (Grievance Disposal).

Check families:
  1. STATUS_IDENTITY   — Opening + Additions = Fully + Partial + Rejected + Pending
  2. COMPLAINT_SUM     — Sum of detail rows ≈ Total Number row (per metric column)
  3. RATIO_SANITY      — Complaint rate per 10K plausibility (WARN only)
  4. COMPLETENESS      — Mandatory rows must be present

Dropping duration-related checks (DURATION_BUCKET_SUM, CROSS_TABLE_PENDING)
per scope change — Table 3 not extracted.
"""

import csv
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional

from config.row_registry import NL45_ROW_ORDER, SUMMARY_ROW
from config.settings import STATUS_METRICS
from extractor.models import NL45Extract

logger = logging.getLogger(__name__)

TOLERANCE = 2.0

# Complaint types that are detail rows (not the total row)
DETAIL_ROWS = [r for r in NL45_ROW_ORDER if r != SUMMARY_ROW]


@dataclass
class ValidationResult:
    company: str
    quarter: str
    year: str
    complaint_type: str   # canonical key, or "ALL" for column-level checks
    check_name: str
    status: str           # PASS / WARN / FAIL / SKIP
    expected: Optional[float]
    actual: Optional[float]
    delta: Optional[float]
    note: str


def run_validations(extractions: List[NL45Extract]) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    for exc in extractions:
        results.extend(_check_completeness(exc))
        if exc.status_data:
            for complaint_type in NL45_ROW_ORDER:
                r = _check_status_identity(exc, complaint_type)
                if r:
                    results.append(r)
            for metric in STATUS_METRICS:
                r = _check_complaint_sum(exc, metric)
                if r:
                    results.append(r)
        if exc.benchmark_data and exc.status_data:
            results.extend(_check_ratio_sanity(exc))
    return results


# ---------------------------------------------------------------------------
# Check 1: STATUS_IDENTITY
# ---------------------------------------------------------------------------

def _check_status_identity(exc: NL45Extract, complaint_type: str) -> Optional[ValidationResult]:
    """Opening + Additions = Fully + Partial + Rejected + Pending_EoQ"""
    metrics = exc.status_data.data.get(complaint_type, {})

    opening  = metrics.get("opening_balance") or 0.0
    additions = metrics.get("additions") or 0.0
    fully    = metrics.get("fully_accepted") or 0.0
    partial  = metrics.get("partial_accepted") or 0.0
    rejected = metrics.get("rejected") or 0.0
    pending  = metrics.get("pending_eoq") or 0.0

    lhs = opening + additions
    rhs = fully + partial + rejected + pending

    # Skip all-zero rows (no complaints in this category)
    if lhs == 0.0 and rhs == 0.0:
        return ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            complaint_type, "STATUS_IDENTITY", "SKIP",
            expected=None, actual=None, delta=None,
            note="All values zero — no complaints in this category",
        )

    delta = abs(lhs - rhs)
    status = "PASS" if delta <= TOLERANCE else ("WARN" if delta <= 5.0 else "FAIL")

    return ValidationResult(
        exc.company_name, exc.quarter, exc.year,
        complaint_type, "STATUS_IDENTITY", status,
        expected=lhs, actual=rhs, delta=delta,
        note="" if status == "PASS" else f"Opening+Additions={lhs}, Resolved+Pending={rhs}",
    )


# ---------------------------------------------------------------------------
# Check 2: COMPLAINT_SUM
# ---------------------------------------------------------------------------

def _check_complaint_sum(exc: NL45Extract, metric: str) -> Optional[ValidationResult]:
    """Sum of detail rows should ≈ total_complaints row for each metric."""
    total_metrics = exc.status_data.data.get(SUMMARY_ROW, {})
    total_val = total_metrics.get(metric)

    if total_val is None:
        return ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            "ALL", f"COMPLAINT_SUM_{metric.upper()}", "SKIP",
            expected=None, actual=None, delta=None,
            note=f"Total row missing value for {metric}",
        )

    computed = sum(
        exc.status_data.data.get(ct, {}).get(metric) or 0.0
        for ct in DETAIL_ROWS
    )

    delta = abs(total_val - computed)
    status = "PASS" if delta <= TOLERANCE else "FAIL"

    return ValidationResult(
        exc.company_name, exc.quarter, exc.year,
        "ALL", f"COMPLAINT_SUM_{metric.upper()}", status,
        expected=computed, actual=total_val, delta=delta,
        note="" if status == "PASS" else f"Sum of details={computed}, Total row={total_val}",
    )


# ---------------------------------------------------------------------------
# Check 3: RATIO_SANITY (WARN only — formula not precisely defined in PDF)
# ---------------------------------------------------------------------------

def _check_ratio_sanity(exc: NL45Extract) -> List[ValidationResult]:
    """
    Companies fill benchmark ratios using different numerator bases:
      - Some use claim/policy YTD totals (total_registered_ytd for that type)
      - Some use quarterly additions for that complaint type
      - Some count all non-claim complaints as "policy complaints"
    Try all plausible candidates and take the best match.
    """
    results = []
    bm = exc.benchmark_data
    sd = exc.status_data.data

    total_row   = sd.get(SUMMARY_ROW, {})
    claim_row   = sd.get("claim", {})
    policy_row  = sd.get("policy_related", {})

    total_ytd    = total_row.get("total_registered_ytd") or 0.0
    claim_ytd    = claim_row.get("total_registered_ytd") or 0.0
    claim_add    = claim_row.get("additions") or 0.0
    policy_ytd   = policy_row.get("total_registered_ytd") or 0.0
    policy_add   = policy_row.get("additions") or 0.0
    non_claim_ytd = total_ytd - claim_ytd

    def _best(candidates, pdf_val):
        """Return (best_computed, best_delta) from a list of candidate numerators."""
        best_computed, best_delta = None, float("inf")
        for c in candidates:
            if c is None or c == 0.0:
                continue
            delta = abs(c - pdf_val)
            if delta < best_delta:
                best_delta = delta
                best_computed = c
        return best_computed, best_delta

    # Policy ratio — candidates differ by company (non-claim YTD, policy_related YTD, policy additions)
    if bm.policies_curr_year and bm.policy_complaints_per_10k is not None:
        p = bm.policies_curr_year
        pdf_val = bm.policy_complaints_per_10k
        candidates = [
            non_claim_ytd / p * 10_000 if non_claim_ytd else None,
            policy_ytd    / p * 10_000 if policy_ytd    else None,
            policy_add    / p * 10_000 if policy_add    else None,
        ]
        best_computed, best_delta = _best(candidates, pdf_val)
        if best_computed is None:
            return results
        status = "PASS" if best_delta / max(abs(pdf_val), 0.01) <= 0.30 else "WARN"
        results.append(ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            "ALL", "RATIO_SANITY_POLICY", status,
            expected=best_computed, actual=pdf_val, delta=best_delta,
            note="Best-match across numerator variants (non-claim YTD / policy YTD / policy additions)",
        ))

    # Claim ratio — candidates: claim YTD or claim quarterly additions
    if bm.claims_curr_year and bm.claim_complaints_per_10k is not None:
        c = bm.claims_curr_year
        pdf_val = bm.claim_complaints_per_10k
        candidates = [
            claim_ytd / c * 10_000 if claim_ytd else None,
            claim_add / c * 10_000 if claim_add else None,
        ]
        best_computed, best_delta = _best(candidates, pdf_val)
        if best_computed is None:
            return results
        status = "PASS" if best_delta / max(abs(pdf_val), 0.01) <= 0.30 else "WARN"
        results.append(ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            "ALL", "RATIO_SANITY_CLAIM", status,
            expected=best_computed, actual=pdf_val, delta=best_delta,
            note="Best-match across numerator variants (claim YTD / claim additions)",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 4: COMPLETENESS
# ---------------------------------------------------------------------------

def _check_completeness(exc: NL45Extract) -> List[ValidationResult]:
    results = []

    if not exc.status_data or not exc.status_data.data:
        results.append(ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            "ALL", "COMPLETENESS", "FAIL",
            expected=None, actual=None, delta=None,
            note="status_data is empty — extraction failed",
        ))
        return results

    # Total row must be present with at least 5 of 7 metrics
    total_metrics = exc.status_data.data.get(SUMMARY_ROW, {})
    non_none_count = sum(1 for v in total_metrics.values() if v is not None)
    if not total_metrics:
        results.append(ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            SUMMARY_ROW, "COMPLETENESS", "FAIL",
            expected=None, actual=None, delta=None,
            note="'Total Number' row is missing from extraction",
        ))
    elif non_none_count < 5:
        results.append(ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            SUMMARY_ROW, "COMPLETENESS", "WARN",
            expected=7.0, actual=float(non_none_count), delta=None,
            note=f"Total row has only {non_none_count}/7 metric values",
        ))

    # Claim row must be present (highest-volume category, always populated)
    claim_metrics = exc.status_data.data.get("claim", {})
    if not claim_metrics or all(v is None for v in claim_metrics.values()):
        results.append(ValidationResult(
            exc.company_name, exc.quarter, exc.year,
            "claim", "COMPLETENESS", "WARN",
            expected=None, actual=None, delta=None,
            note="'Claim' row is entirely missing or all-None",
        ))

    return results


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_validation_report(results: List[ValidationResult], output_path: str):
    fieldnames = [
        "company", "quarter", "year", "complaint_type",
        "check_name", "status", "expected", "actual", "delta", "note",
    ]

    # Keys of companies being written in this run — used to evict stale rows
    new_keys = {(r.company, r.quarter, r.year) for r in results}

    existing: List[dict] = []
    import os
    if os.path.exists(output_path):
        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and reader.fieldnames[:len(fieldnames)] == fieldnames:
                for row in reader:
                    key = (row.get("company"), row.get("quarter"), row.get("year"))
                    if key not in new_keys:
                        existing.append(row)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing:
            writer.writerow({k: row.get(k) for k in fieldnames})
        for r in results:
            writer.writerow(asdict(r))
    logger.info(f"Validation report saved to {output_path}")
