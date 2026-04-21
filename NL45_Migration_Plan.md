# NL45 Migration Plan — Grievance Disposal

**Status:** Draft — Plan Only (no code written)  
**Reference PDF:** `Desktop/Forms/Fy2026/Q3/NL45/NL45_BajajGeneral.pdf`  
**Sample company:** Bajaj General Insurance Ltd, Q3 FY2025-26 (as at 31st Dec'25)  
**Closest prior extractor:** NL44 (Motor TP) — simplest direct-column pattern  
**Secondary reference:** NL39 (Claims Ageing) — multi-table Excel output pattern

---

## A. High-Level Summary

### Form Identity

| Field | Value |
|---|---|
| IRDAI Form | NL-45 |
| Title | GRIEVANCE DISPOSAL |
| Disclosure Type | Periodic (Quarterly) |
| Period | Current quarter only; Total column is cumulative YTD |

### Data Shape

NL-45 contains **three logically distinct tables** on a single PDF page:

| Table | Axes | Shape (per company per quarter) |
|---|---|---|
| **1. Complaint Status Grid** | 9 complaint types × 7 status metrics | 9 data rows + 1 total row |
| **2. Benchmark / Ratio Metrics** | 6 standalone scalar metrics | 6 key-value rows |
| **3. Duration-wise Pending** | 4 duration buckets × 3 groups × 2 metrics | 5 rows × 6 columns |

### Row Axis (Table 1)

Complaint types run down the rows. The section header "Complaints made by customers" is a non-data label. The nine data rows are lettered a–g2 in the PDF (the unusual g/g1/g2 suffix indicates g1 and g2 were appended to the original form without renumbering g).

### Column Axis (Table 1)

**Exact PDF column order** (left to right):

| PDF Position | Column Name | Time Dimension | Notes |
|---|---|---|---|
| 1 | Opening Balance * | QTR start | Carried forward from prior quarter closing |
| 2 | Additions during the quarter (net of duplicate complaints) | FOR THE QUARTER | Net of duplicates |
| 3 | Fully Accepted | FOR THE QUARTER | Sub-column of "Complaints Resolved" |
| 4 | Partial Accepted | FOR THE QUARTER | Sub-column of "Complaints Resolved" |
| 5 | Rejected | FOR THE QUARTER | Sub-column of "Complaints Resolved" |
| 6 | Complaints Pending at the end of the quarter | QTR end snapshot | Comes **after** resolved columns — counter-intuitive; parser must handle |
| 7 | Total Complaints registered up to the quarter during the financial year | **CUMULATIVE YTD** | Only column that is YTD, not QTR |

> **Critical note:** Columns 3-5 are sub-columns under the merged header "Complaints Resolved". Column 6 (Pending) sits after the Resolved group, not before it. The identity is: `Opening + Additions = Fully + Partial + Rejected + Pending`.

### Period Structure

- **No CY/PY split** in Table 1 — all values reflect the current quarter/year only.
- **No Quarter_Info dimension** needed — each column already encodes its own time scope (QTR vs YTD is inherent per column, not a row multiplier).
- Benchmark rows include prior-year reference counts (Rows 2–3) alongside current-year counts (Rows 4–5).

### Reuse Classification

| Component | Source | Action |
|---|---|---|
| `normaliser.py` | NL44 | Copy unchanged |
| `path_scanner.py` | NL44 | Copy unchanged |
| `processed_log.py` | NL44 | Copy unchanged |
| `company_metadata.py` | NL44 | Copy unchanged |
| `company_registry.py` | NL44 | Minor edit (update form_type reference) |
| `consolidated_detector.py` | NL44 | Minor edit (add NL-45 page detection) |
| `main.py` | NL44 | Minor edit (rename extractor) |
| `pipeline.py` | NL44 | Minor edit (update pipeline config) |
| All config files | — | Full rewrite |
| `models.py` | — | Full rewrite |
| `_base_nl45.py` | — | New (no equivalent in NL44) |
| `parser.py` | — | Full rewrite |
| `excel_writer.py` | — | Full rewrite |
| `checks.py` | — | Full rewrite |

---

## B. Canonical Row Keys and Aliases

### B1. Complaint Status Rows (Table 1)

**`NL45_ROW_ORDER`** — in PDF order:

```
proposal_related
claim
policy_related
premium
refund
coverage
cover_note_related
product
others
total_complaints          ← summary row
```

**`NL45_ROW_DISPLAY_NAMES`**:

```python
{
    "proposal_related":    "Proposal Related",
    "claim":               "Claim",
    "policy_related":      "Policy Related",
    "premium":             "Premium",
    "refund":              "Refund",
    "coverage":            "Coverage",
    "cover_note_related":  "Cover Note Related",
    "product":             "Product",
    "others":              "Others (to be specified)",
    "total_complaints":    "Total Number",
}
```

**`NL45_ROW_ALIASES`** — normalised label text → canonical key:

```python
{
    # proposal_related
    "proposal related":                       "proposal_related",
    "proposal":                               "proposal_related",
    "proposals":                              "proposal_related",
    "proposal related complaints":            "proposal_related",

    # claim
    "claim":                                  "claim",
    "claims":                                 "claim",
    "claim related":                          "claim",
    "claim complaints":                       "claim",

    # policy_related
    "policy related":                         "policy_related",
    "policy":                                 "policy_related",
    "policies":                               "policy_related",
    "policy related complaints":              "policy_related",

    # premium
    "premium":                                "premium",
    "premium related":                        "premium",

    # refund
    "refund":                                 "refund",
    "refunds":                                "refund",
    "refund related":                         "refund",

    # coverage
    "coverage":                               "coverage",
    "coverage related":                       "coverage",

    # cover_note_related
    "cover note related":                     "cover_note_related",
    "cover note":                             "cover_note_related",
    "covernote related":                      "cover_note_related",
    "covernote":                              "cover_note_related",

    # product
    "product":                                "product",
    "products":                               "product",
    "product related":                        "product",

    # others (consolidates the (i) and (ii) blank lines)
    "others (to be specified)":               "others",
    "others":                                 "others",
    "other":                                  "others",
    "others to be specified":                 "others",

    # total
    "total number":                           "total_complaints",
    "total":                                  "total_complaints",
    "total no.":                              "total_complaints",
    "total no. of complaints":                "total_complaints",
}
```

**`NL45_SKIP_PATTERNS`** — rows to ignore during parsing:

```python
[
    re.compile(r"^form\s+nl[-\s]?45", re.IGNORECASE),
    re.compile(r"^periodic\s+disclosures", re.IGNORECASE),
    re.compile(r"^gri[e]?vance\s+disposal", re.IGNORECASE),
    re.compile(r"^grievance\s+disposal\s+for\s+the\s+period", re.IGNORECASE),
    re.compile(r"^complaints\s+made\s+by\s+customers?", re.IGNORECASE),   # section header
    re.compile(r"^complaints\s+made\s+by\s+intermediari", re.IGNORECASE), # section header
    re.compile(r"^sl\.?\s*no", re.IGNORECASE),
    re.compile(r"^particulars?$", re.IGNORECASE),
    re.compile(r"^opening\s+balance", re.IGNORECASE),                     # col header row
    re.compile(r"^additions\s+during", re.IGNORECASE),                    # col header row
    re.compile(r"^complaints\s+resolved", re.IGNORECASE),                 # col header row
    re.compile(r"^fully\s+accept", re.IGNORECASE),                        # sub-header
    re.compile(r"^partial\s+accept", re.IGNORECASE),                      # sub-header
    re.compile(r"^rejected?$", re.IGNORECASE),                            # sub-header
    re.compile(r"^complaints\s+pending", re.IGNORECASE),                  # col header row
    re.compile(r"^total\s+complaints\s+registered", re.IGNORECASE),       # col header row
    re.compile(r"^note\s*[:\–\-]", re.IGNORECASE),                       # footnote
    re.compile(r"^\(?[a-e]\)"),                                           # footnote bullets (a)-(e)
    re.compile(r"^from\s+the\s+overall", re.IGNORECASE),                  # inline note
    re.compile(r"^\s*\(i+\)\s*_+\s*$"),                                   # blank (i)____ specifier lines
    re.compile(r"^\s*\(ii+\)\s*_+\s*$"),                                  # blank (ii)____ specifier lines
]
```

### B2. Duration-wise Pending Bucket Keys (Table 3)

**`NL45_DURATION_ORDER`**:

```
up_to_15d
d15_30
d30_90
d90_plus
total_pending_duration    ← "Total No. of complaints" row
```

**`NL45_DURATION_ALIASES`**:

```python
{
    "up to 15 days":              "up_to_15d",
    "upto 15 days":               "up_to_15d",
    "up to 15":                   "up_to_15d",
    "15-30 days":                 "d15_30",
    "15 30 days":                 "d15_30",
    "15 to 30 days":              "d15_30",
    "30-90 days":                 "d30_90",
    "30 90 days":                 "d30_90",
    "30 to 90 days":              "d30_90",
    "90 days & beyond":           "d90_plus",
    "90 days and beyond":         "d90_plus",
    "90 days beyond":             "d90_plus",
    "90 days +:":                 "d90_plus",
    "total no. of complaints":    "total_pending_duration",
    "total no of complaints":     "total_pending_duration",
    "total":                      "total_pending_duration",
}
```

**`NL45_DURATION_GROUPS`** — three column groups in Table 3:

```python
NL45_DURATION_GROUPS = ["customers", "intermediaries", "total"]
```

Each group contributes two values: `count` and `pct_of_pending`.

### B3. Benchmark Metric Keys (Table 2)

Stored separately; not included in the main MASTER_COLUMNS.

```python
NL45_BENCHMARK_KEYS = [
    "policies_prev_year",          # Row 2
    "claims_prev_year",            # Row 3
    "policies_curr_year",          # Row 4
    "claims_curr_year",            # Row 5
    "policy_complaints_per_10k",   # Row 6 — customer ratio
    "claim_complaints_per_10k",    # Row 7
]
```

---

## C. MASTER_COLUMNS Definition

NL-45's primary analytical unit is **one row per complaint type per company per quarter**. The seven status metrics are direct columns (no Quarter_Info multiplier — each column already encodes its own time scope).

### C1. MASTER_COLUMNS (Table 1 — Complaint Status)

```python
MASTER_COLUMNS = [
    "Complaint_Type",           # A  — canonical key (e.g. "claim")
    "Complaint_Display",        # B  — display label (e.g. "Claim")
    "Company_Name",             # C
    "Company",                  # D  — company_key snake_case
    "NL",                       # E  — always "NL45"
    "Quarter",                  # F  — e.g. "Q3"
    "Year",                     # G  — e.g. "202526"
    "Sector",                   # H
    "Industry_Competitors",     # I
    "GI_Companies",             # J
    # --- Seven NL-45 status metrics ---
    "Opening_Balance",          # K  — carry-forward from prior quarter
    "Additions",                # L  — net of duplicates, FOR THE QUARTER
    "Fully_Accepted",           # M  — resolved, FOR THE QUARTER
    "Partial_Accepted",         # N  — resolved, FOR THE QUARTER
    "Rejected",                 # O  — resolved, FOR THE QUARTER
    "Pending_EoQ",              # P  — end-of-quarter snapshot
    "Total_Registered_YTD",     # Q  — cumulative for the financial year
    "Source_File",              # R
]
```

> `col.lower().replace("_", "")` **does NOT** equal the metric key here (unlike NL44), because some column names are multi-word. The metric key mapping is handled explicitly in `settings.py` via `STATUS_COL_TO_METRIC`.

### C2. MASTER_COLUMNS_DURATION (Table 3 — Duration-wise Pending)

Written to a separate sheet **`Duration_Data`** in the same output workbook.

```python
MASTER_COLUMNS_DURATION = [
    "Duration_Bucket",            # A  — canonical key (e.g. "up_to_15d")
    "Duration_Display",           # B  — display label (e.g. "Up to 15 days")
    "Company_Name",               # C
    "Company",                    # D
    "NL",                         # E  — always "NL45"
    "Quarter",                    # F
    "Year",                       # G
    "Sector",                     # H
    "Industry_Competitors",       # I
    "GI_Companies",               # J
    "Customer_Count",             # K
    "Customer_Pct",               # L  — as decimal (e.g. 1.00 for 100%)
    "Intermediary_Count",         # M
    "Intermediary_Pct",           # N
    "Total_Count",                # O
    "Total_Pct",                  # P
    "Source_File",                # Q
]
```

### C3. STATUS_COL_TO_METRIC mapping (in `settings.py`)

```python
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
```

---

## D. File-by-File Breakdown

### D1. Directory Structure

```
nl45_extractor/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── row_registry.py
│   ├── duration_registry.py          ← new file (no NL44 equivalent)
│   ├── company_metadata.py
│   └── company_registry.py
├── extractor/
│   ├── __init__.py
│   ├── companies/
│   │   ├── __init__.py
│   │   └── _base_nl45.py             ← new file (no NL44 equivalent)
│   ├── models.py
│   ├── normaliser.py
│   ├── parser.py
│   ├── consolidated_detector.py
│   ├── path_scanner.py
│   └── processed_log.py
├── output/
│   ├── __init__.py
│   └── excel_writer.py
├── validation/
│   ├── __init__.py
│   └── checks.py
├── tests/
│   ├── test_row_registry.py
│   ├── test_normaliser.py
│   ├── test_parser.py
│   └── test_checks.py
├── main.py
├── pipeline.py
└── extraction_config.yaml
```

### D2. File Status Table

| File | Status | Change Description |
|---|---|---|
| `config/__init__.py` | COPY | Unchanged from NL44 |
| `config/settings.py` | **REWRITE** | New MASTER_COLUMNS, MASTER_COLUMNS_DURATION, STATUS_COL_TO_METRIC |
| `config/row_registry.py` | **REWRITE** | NL45_ROW_ORDER, aliases, skip patterns, duration keys |
| `config/duration_registry.py` | **NEW** | NL45_DURATION_ORDER, NL45_DURATION_ALIASES, NL45_DURATION_GROUPS |
| `config/company_metadata.py` | COPY | Unchanged from NL44 |
| `config/company_registry.py` | MINOR EDIT | Update `form_type` field from "NL44" to "NL45" |
| `extractor/__init__.py` | COPY | Unchanged from NL44 |
| `extractor/companies/__init__.py` | COPY | Unchanged from NL44 |
| `extractor/companies/_base_nl45.py` | **NEW** | Page detection, column index mapping, status grid extractor, duration grid extractor |
| `extractor/models.py` | **REWRITE** | NL45StatusData, NL45DurationData, NL45BenchmarkData, NL45Extract |
| `extractor/normaliser.py` | COPY | Unchanged from NL44 |
| `extractor/parser.py` | **REWRITE** | Orchestrates _base_nl45 for both status and duration tables |
| `extractor/consolidated_detector.py` | MINOR EDIT | Add NL-45 page keyword patterns |
| `extractor/path_scanner.py` | COPY | Unchanged from NL44 |
| `extractor/processed_log.py` | COPY | Unchanged from NL44 |
| `output/__init__.py` | COPY | Unchanged from NL44 |
| `output/excel_writer.py` | **REWRITE** | Two-sheet output (Master_Data + Duration_Data) + per-company verification |
| `validation/__init__.py` | COPY | Unchanged from NL44 |
| `validation/checks.py` | **REWRITE** | Six new NL45-specific checks (see Section F) |
| `tests/test_row_registry.py` | **REWRITE** | Alias coverage tests for NL45 labels |
| `tests/test_normaliser.py` | COPY | Unchanged (same normaliser) |
| `tests/test_parser.py` | **REWRITE** | Parser tests against Bajaj sample PDF |
| `tests/test_checks.py` | **REWRITE** | Validation check tests with synthetic NL45Extract fixtures |
| `main.py` | MINOR EDIT | Update module name and extractor label |
| `pipeline.py` | MINOR EDIT | Update pipeline config for NL45 |
| `extraction_config.yaml` | **NEW** | NL45-specific YAML config |

---

## E. New Config / Metadata Files

### E1. `config/settings.py` — key additions beyond NL44

```python
EXTRACTOR_VERSION = "1.0.0"
NUMBER_FORMAT = "#,##0.00"
PCT_FORMAT = "0.00%"
LOW_CONFIDENCE_FILL_COLOR = "FFFF99"

MASTER_COLUMNS = [ ... ]           # See Section C1
MASTER_COLUMNS_DURATION = [ ... ]  # See Section C2

STATUS_COL_TO_METRIC = { ... }     # See Section C3
STATUS_METRICS = list(STATUS_COL_TO_METRIC.values())

# PDF column index → metric key (0-indexed, after Sl No. and Particulars columns)
# Actual indices depend on pdfplumber table extraction and must be confirmed
# during implementation against the sample PDF.
# Best-guess from PDF structure:
#   col 0 = sl_no, col 1 = particulars
#   col 2 = opening_balance
#   col 3 = additions
#   col 4 = fully_accepted
#   col 5 = partial_accepted
#   col 6 = rejected
#   col 7 = pending_eoq
#   col 8 = total_registered_ytd
STATUS_COLUMN_INDICES = {
    2: "opening_balance",
    3: "additions",
    4: "fully_accepted",
    5: "partial_accepted",
    6: "rejected",
    7: "pending_eoq",
    8: "total_registered_ytd",
}

# For duration table, column index mapping (per group):
# Group order: Customers (cols 1-2), Intermediaries (cols 3-4), Total (cols 5-6)
# col 0 = duration bucket label
DURATION_GROUP_COLUMN_PAIRS = {
    "customers":      (1, 2),   # (count_col, pct_col)
    "intermediaries": (3, 4),
    "total":          (5, 6),
}
```

### E2. `config/duration_registry.py` — new file

Contains `NL45_DURATION_ORDER`, `NL45_DURATION_ALIASES`, `NL45_DURATION_DISPLAY_NAMES`, and `NL45_DURATION_GROUPS` as defined in Section B2.

### E3. `extraction_config.yaml` — new file

```yaml
extractor: NL45
version: "1.0.0"
form_type: NL45
form_title: "GRIEVANCE DISPOSAL"
irdai_form_code: "NL-45"
input_dir: "input/"
output_dir: "output/"
log_level: INFO
tables:
  status:
    sheet_name: "Master_Data"
    row_label_col: 1        # "Particulars" column index
    data_start_col: 2       # First metric column index
  duration:
    sheet_name: "Duration_Data"
    label_col: 0            # Duration bucket label column index
    data_start_col: 1
```

---

## F. Validation Checks

All checks use `TOLERANCE = 2.0` (complaint counts are small integers; rounding errors are ≤1).

### Check 1: `STATUS_IDENTITY` — Row-level conservation identity

**Formula:** `Opening_Balance + Additions = Fully_Accepted + Partial_Accepted + Rejected + Pending_EoQ`

- Applies to every complaint type row AND the Total row.
- SKIP if all values for that row are zero or None (e.g., Cover Note Related for many companies).
- Status: PASS if `|delta| ≤ TOLERANCE`, WARN if `TOLERANCE < |delta| ≤ 5`, FAIL otherwise.
- Note (a) in PDF mandates this reconciliation.

```
ValidationResult fields: company, quarter, year, complaint_type, check_name, status,
                         expected (lhs), actual (rhs), delta, note
```

### Check 2: `COMPLAINT_TYPE_SUM` — Column-level totals check

**Formula:** For each of the 7 status metrics:
`sum(proposal_related ... others) ≈ total_complaints`

- Applies to all 7 columns independently.
- SKIP the `Total_Registered_YTD` column for this check if individual rows' YTD values are not stored separately (implementation choice — see Open Questions).
- Status: PASS / FAIL.

### Check 3: `DURATION_BUCKET_SUM` — Duration totals integrity

**Formula (per group: customers, intermediaries, total):**
`up_to_15d + d15_30 + d30_90 + d90_plus ≈ total_pending_duration`

- Applies to both `count` and `pct` values.
- For percentages: `pct` sum should be ≈ 1.00 (100%) for non-zero groups.
- Status: PASS / WARN (percentages may not sum exactly to 100% due to rounding).

### Check 4: `CROSS_TABLE_PENDING` — Pending count cross-table consistency

**Formula:**
`Pending_EoQ (Total row in status table) ≈ Total_Count (total_pending_duration row in duration table)`

- This is the primary cross-table validation.
- Status: PASS if `|delta| ≤ TOLERANCE`, FAIL otherwise.
- If either table failed to extract, SKIP with note.

### Check 5: `RATIO_SANITY` — Policy and claim complaint rate plausibility

**Formula (approximate — IRDAI definition not fully specified in PDF):**
```
policy_complaints_per_10k ≈ (total_complaints_ytd / policies_curr_year) × 10,000
claim_complaints_per_10k  ≈ (total_complaints_ytd / claims_curr_year)   × 10,000
```

- Reported as WARN only (not FAIL), because the exact numerator definition is ambiguous (see Open Questions Q1).
- SKIP if benchmark metrics were not extracted.
- Acceptable delta: ±30% of reported value.

### Check 6: `COMPLETENESS` — Mandatory rows present

- The `claim` row and `total_complaints` row must have at least one non-None metric value.
- All 7 status metric values must be non-None for `total_complaints`.
- WARN (not FAIL) for individual complaint type rows being all-None, because some companies may legitimately have no complaints in a category.
- FAIL if `total_complaints` row is entirely absent.

---

## G. Test Rewrite Scope

All four test files require a full rewrite. The NL44 tests are not reusable because the data model and form structure differ fundamentally.

### `test_row_registry.py`

- Verify every alias in `NL45_ROW_ALIASES` resolves to a key in `NL45_ROW_ORDER`.
- Verify every alias in `NL45_DURATION_ALIASES` resolves to a key in `NL45_DURATION_ORDER`.
- Verify no alias maps to a non-existent key.
- Verify `normalise_text(pdf_label)` → alias → key round-trip for each observed PDF label.
- Test PDF labels from Bajaj sample: "Proposal Related", "Claim", "Policy Related", "Premium", "Refund", "Coverage", "Cover Note Related", "Product", "Others (to be specified)", "Total Number".
- Test duration labels: "Up to 15 days", "15-30 days", "30-90 days", "90 days & Beyond", "Total No. of complaints".

### `test_normaliser.py`

- Copy from NL44 unchanged (same `clean_number` and `normalise_text` contract).
- Add one NL45-specific case: percentage strings like "100%" → 1.0 or 100.0 (confirm which representation is used for `pct` storage).

### `test_parser.py`

Use the Bajaj sample PDF as a fixture. Assert extracted values for:

**Status table:**
```
claim: opening=6, additions=789, fully_accepted=178, partial_accepted=0,
       rejected=615, pending_eoq=2, total_registered_ytd=2075
total_complaints: opening=6, additions=1357, fully_accepted=482, partial_accepted=0,
                  rejected=877, pending_eoq=4, total_registered_ytd=3380
```

**Duration table:**
```
up_to_15d: customer_count=4, customer_pct=1.00, intermediary_count=0,
           intermediary_pct=0.00, total_count=4, total_pct=1.00
total_pending_duration: customer_count=4, total_count=4
```

**Benchmark metrics:**
```
policies_curr_year=27474096, claims_curr_year=4385293
policy_complaints_per_10k=0.47, claim_complaints_per_10k=4.73
```

### `test_checks.py`

Build synthetic `NL45Extract` fixtures:

1. **Perfect fixture** — all 6 checks PASS.
2. **Identity violation** — one complaint type has `Opening + Additions ≠ Resolved + Pending`; assert `STATUS_IDENTITY` FAIL.
3. **Sum mismatch** — total row does not equal sum of types; assert `COMPLAINT_TYPE_SUM` FAIL.
4. **Duration mismatch** — duration bucket counts do not sum to total_pending_duration; assert `DURATION_BUCKET_SUM` WARN.
5. **Cross-table mismatch** — `Pending_EoQ` (status) ≠ `Total_Count` (duration); assert `CROSS_TABLE_PENDING` FAIL.
6. **Missing total row** — total_complaints row absent; assert `COMPLETENESS` FAIL.
7. **All-zero company** — all complaint types zero; assert `STATUS_IDENTITY` SKIP (not FAIL).

---

## H. Open Questions / Ambiguities

These must be resolved before implementation begins. No assumptions have been made in the plan above.

**Q1 — Ratio numerator definition (Row 6 / Row 7)**

The PDF shows `policy_complaints_per_10k = 0.47` for Bajaj Q3. The formula "Total policy complaints / Total policies × 10,000" does not reproduce this value precisely with any obvious numerator (see working below). The exact IRDAI definition of "policy complaints" vs "all complaints" must be confirmed.

```
Attempt: all_additions_qtd (1357) / policies_curr_year (27474096) × 10000 = 0.4939  ≠ 0.47
Attempt: total_registered_ytd (3380) / policies_curr_year (27474096) × 10000 = 1.23  ≠ 0.47
Attempt: policy_related_ytd (787) / policies_curr_year (27474096) × 10000 = 0.286   ≠ 0.47
```
The denominator or numerator basis is unclear. The `ratio_sanity` check should be WARN-only until confirmed.

**Q2 — Intermediary complaint table location**

Note (e) in the PDF states: *"For 1 to 7 Similar break-up to be given for the complaints made by intermediaries."* In the Bajaj sample, no separate intermediary complaint grid appears in the main status table. Either:
- (a) Intermediary complaints appear on a second page not included in the sample PDF; or
- (b) Intermediary complaints are shown as an additional section within the same page for companies that have intermediary complaints; or
- (c) The intermediary breakdown is embedded as additional rows in the same table (e.g., rows with a "source" prefix).

**Resolution needed:** Obtain a multi-page NL45 sample or one where intermediary complaints are non-zero to confirm layout.

**Q3 — Row 6 second value**

Row 6 displays `0.47` and then `-` (a second value separated by a dash or empty cell). This may represent:
- (a) Customer ratio | Intermediary ratio (with intermediary = 0, shown as `-`); or
- (b) Customer rate | Change from prior quarter.

**Resolution needed:** Examine a PDF where both customer and intermediary ratios are non-zero.

**Q4 — "Others" consolidation**

The PDF shows g2 as a single row labelled "Others (to be specified)" with two blank sub-specifiers `(i)___` and `(ii)___`. The Bajaj data shows a combined value (124 additions). Do some companies:
- (a) Report (i) and (ii) as separate rows with custom labels, adding two rows to the table; or
- (b) Always consolidate them into one "Others" row?

If (a), the parser needs to handle variable-length tables and consolidate custom rows into the `others` key.

**Q5 — Column index stability**

The Bajaj PDF's table may have merged cells for "Complaints Resolved" (spanning Fully / Partial / Rejected), which pdfplumber may or may not split correctly. The actual column indices in `STATUS_COLUMN_INDICES` must be confirmed by running pdfplumber against the sample and printing raw table output before writing the base extractor.

---

## I. Implementation Order

Recommended build sequence (each step is independently testable):

1. `config/row_registry.py` + `config/duration_registry.py` → `tests/test_row_registry.py`
2. `config/settings.py` (MASTER_COLUMNS, STATUS_COLUMN_INDICES)
3. `extractor/models.py` (data structures only)
4. `extractor/companies/_base_nl45.py` (page detection + column index confirmation against raw pdfplumber output)
5. `extractor/parser.py` → `tests/test_parser.py` (against Bajaj PDF)
6. `output/excel_writer.py` (Master_Data + Duration_Data sheets)
7. `validation/checks.py` → `tests/test_checks.py`
8. `extractor/consolidated_detector.py` (minor edit)
9. `pipeline.py` + `main.py` + `extraction_config.yaml` (integration)

Resolve Q1-Q5 before or during step 4.
