"""
Global constants for the NL-45 Extractor (Grievance Disposal).

Master sheet layout:
  - One row per (company × quarter × complaint_type)
  - Seven NL-45 status metrics as direct columns (no Quarter_Info multiplier)
  - Each column already encodes its own time scope inherently
"""

EXTRACTOR_VERSION = "1.0.0"
NUMBER_FORMAT = "#,##0.00"
LOW_CONFIDENCE_FILL_COLOR = "FFFF99"

MASTER_COLUMNS = [
    "Complaint_Type",           # A  — canonical key (e.g. "claim")
    "Complaint_Display",        # B  — human-readable PDF label (e.g. "Claim")
    "Company_Name",             # C
    "Company",                  # D  — company_key snake_case (sorted prefix)
    "NL",                       # E  — always "NL45"
    "Quarter",                  # F  — e.g. "Q3"
    "Year",                     # G  — e.g. "26" (FY end year)
    "Sector",                   # H
    "Industry_Competitors",     # I
    "GI_Companies",             # J
    # --- Seven NL-45 status metrics (PDF column order) ---
    "Opening_Balance",          # K  — carry-forward from prior quarter closing
    "Additions",                # L  — net of duplicates, FOR THE QUARTER
    "Fully_Accepted",           # M  — resolved, FOR THE QUARTER
    "Partial_Accepted",         # N  — resolved, FOR THE QUARTER
    "Rejected",                 # O  — resolved, FOR THE QUARTER
    "Pending_EoQ",              # P  — end-of-quarter snapshot
    "Total_Registered_YTD",     # Q  — cumulative for the financial year
    "Source_File",              # R
]

# Maps MASTER_COLUMNS metric column name → internal metric key used in data dict.
# col.lower() does NOT equal the key (multi-word names), so explicit mapping is required.
STATUS_COL_TO_METRIC = {
    "Opening_Balance":      "opening_balance",
    "Additions":            "additions",
    "Fully_Accepted":       "fully_accepted",
    "Partial_Accepted":     "partial_accepted",
    "Rejected":             "rejected",
    "Pending_EoQ":          "pending_eoq",
    "Total_Registered_YTD": "total_registered_ytd",
}
STATUS_METRICS = list(STATUS_COL_TO_METRIC.values())

# Confirmed pdfplumber column indices for TABLE 1 — standard 9-column layout (Bajaj, Chola).
# [sl_no, particulars, opening, additions, fully, partial, rejected, pending, total_ytd]
STATUS_COLUMN_INDICES_9 = {
    2: "opening_balance",
    3: "additions",
    4: "fully_accepted",
    5: "partial_accepted",
    6: "rejected",
    7: "pending_eoq",
    8: "total_registered_ytd",
}

# 10-column layout (New India and others with extra "Resolved with no option selected" col).
# [sl_no, particulars, opening, additions, fully, partial, rejected, resolved_no_option, pending, total_ytd]
# col 7 ("resolved with no option selected") is skipped — not in the data model.
STATUS_COLUMN_INDICES_10 = {
    2: "opening_balance",
    3: "additions",
    4: "fully_accepted",
    5: "partial_accepted",
    6: "rejected",
    # col 7 skipped ("resolved with no option selected")
    8: "pending_eoq",
    9: "total_registered_ytd",
}

# Backward-compat alias used by settings import callers that just need "the" mapping.
STATUS_COLUMN_INDICES = STATUS_COLUMN_INDICES_9


def get_status_column_indices(ncols: int) -> dict:
    """Return the right column-index map based on the table's column count."""
    return STATUS_COLUMN_INDICES_10 if ncols >= 10 else STATUS_COLUMN_INDICES_9

# pdfplumber column indices for TABLE 2 (benchmark metrics).
# TABLE 2 has 3 columns: [row_num, label, value]
BENCHMARK_VALUE_COL = 2

# Row numbers (as strings in col[0]) → benchmark metric key
BENCHMARK_ROW_MAP = {
    "2": "policies_prev_year",
    "3": "claims_prev_year",
    "4": "policies_curr_year",
    "5": "claims_curr_year",
    "6": "policy_complaints_per_10k",
    "7": "claim_complaints_per_10k",
}


def company_key_to_pascal(key: str) -> str:
    return key.replace("_", " ").title().replace(" ", "")


def _year_code_to_fy_end(year_code: str) -> str:
    s = str(year_code).strip()
    if len(s) == 8:
        return s[4:]
    if len(s) == 6:
        return f"20{s[4:]}"
    return s
