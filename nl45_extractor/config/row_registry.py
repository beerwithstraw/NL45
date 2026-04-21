"""
Row Registry for NL-45 (Grievance Disposal).

Complaint types as rows; status metrics are direct columns (see settings.py).
Row keys follow PDF order (a–g2, then Total Number).
"""

import re
from typing import Optional, Callable

# Canonical row keys in PDF order.
# "total_complaints" is the summary row (bold in PDF).
NL45_ROW_ORDER = [
    "proposal_related",
    "claim",
    "policy_related",
    "premium",
    "refund",
    "coverage",
    "cover_note_related",
    "product",
    "others",
    "total_complaints",
]

# Exact PDF display text for each canonical key.
NL45_ROW_DISPLAY_NAMES = {
    "proposal_related":   "Proposal Related",
    "claim":              "Claim",
    "policy_related":     "Policy Related",
    "premium":            "Premium",
    "refund":             "Refund",
    "coverage":           "Coverage",
    "cover_note_related": "Cover Note Related",
    "product":            "Product",
    "others":             "Others (to be specified)",
    "total_complaints":   "Total Number",
}

# Normalised label text → canonical key.
# normalise_text() lowercases and collapses whitespace before lookup.
NL45_ROW_ALIASES = {
    # proposal_related
    "proposal related":                     "proposal_related",
    "proposal":                             "proposal_related",
    "proposals":                            "proposal_related",
    "proposal related complaints":          "proposal_related",

    # claim
    "claim":                                "claim",
    "claims":                               "claim",
    "claim related":                        "claim",
    "claims related":                       "claim",
    "claim complaints":                     "claim",

    # policy_related
    "policy related":                       "policy_related",
    "policy":                               "policy_related",
    "policies":                             "policy_related",
    "policy related complaints":            "policy_related",

    # premium
    "premium":                              "premium",
    "premium related":                      "premium",

    # refund
    "refund":                               "refund",
    "refunds":                              "refund",
    "refund related":                       "refund",

    # coverage
    "coverage":                             "coverage",
    "coverage related":                     "coverage",

    # cover_note_related
    "cover note related":                   "cover_note_related",
    "cover note":                           "cover_note_related",
    "covernote related":                    "cover_note_related",
    "covernote":                            "cover_note_related",
    "cover note related complaints":        "cover_note_related",

    # product
    "product":                              "product",
    "products":                             "product",
    "product related":                      "product",

    # others — consolidates the blank (i) and (ii) sub-lines
    "others (to be specified)":             "others",
    "others":                               "others",
    "other":                                "others",
    "others to be specified":               "others",

    # total
    "total number":                         "total_complaints",
    "total no. of complaints":              "total_complaints",
    "total complaints":                     "total_complaints",
    "total no.":                            "total_complaints",
    "sub total":                            "total_complaints",
    "total":                                "total_complaints",
}

# Summary row key — identified separately for validation checks.
SUMMARY_ROW = "total_complaints"

# Rows to skip (header rows, section labels, footnotes, blank specifier lines).
NL45_SKIP_PATTERNS = [
    re.compile(r"form\s+nl[-\s]?45", re.IGNORECASE),
    re.compile(r"periodic\s+disclosures", re.IGNORECASE),
    re.compile(r"gri[e]?vance\s+disposal", re.IGNORECASE),
    re.compile(r"complaints\s+made\s+by\s+customers?", re.IGNORECASE),
    re.compile(r"complaints\s+made\s+by\s+intermediari", re.IGNORECASE),
    re.compile(r"^sl\.?\s*no", re.IGNORECASE),
    re.compile(r"^particulars?$", re.IGNORECASE),
    re.compile(r"^opening\s+balance", re.IGNORECASE),
    re.compile(r"^additions\s+during", re.IGNORECASE),
    re.compile(r"^complaints\s+resolved", re.IGNORECASE),
    re.compile(r"^fully\s+accept", re.IGNORECASE),
    re.compile(r"^partial\s+accept", re.IGNORECASE),
    re.compile(r"^rejected?$", re.IGNORECASE),
    re.compile(r"^complaints\s+pending", re.IGNORECASE),
    re.compile(r"^total\s+complaints\s+registered", re.IGNORECASE),
    re.compile(r"note\s*[:\u2013\-]", re.IGNORECASE),
    re.compile(r"^\(?[a-e]\)\s+opening\s+balance", re.IGNORECASE),
    re.compile(r"^\(?[a-e]\)\s+complaints\s+reported", re.IGNORECASE),
    re.compile(r"^\(?[a-e]\)\s+no\.\s+of\s+policies", re.IGNORECASE),
    re.compile(r"^\(?[a-e]\)\s+claims\s+should", re.IGNORECASE),
    re.compile(r"^\(?[a-e]\)\s+for\s+1\s+to\s+7", re.IGNORECASE),
    re.compile(r"from\s+the\s+overall", re.IGNORECASE),
    re.compile(r"^\s*\([i]+\)\s*_+\s*$"),
]


def resolve_row(label: str, normalise_fn: Callable) -> Optional[str]:
    """Map a raw label to a canonical row key, or None if unrecognised."""
    norm = normalise_fn(label)
    if not norm:
        return None
    if norm in NL45_ROW_ALIASES:
        return NL45_ROW_ALIASES[norm]
    # Substring fallback — sort longest-first so specific aliases win over short ones.
    # e.g. "sub total" (9) beats "other" (5) when matching "sub total (modes other than)".
    for alias, key in sorted(NL45_ROW_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in norm:
            return key
    return None


def should_skip(label: str) -> bool:
    """Return True if this row label should be skipped entirely."""
    for pat in NL45_SKIP_PATTERNS:
        if pat.search(label):
            return True
    return False
