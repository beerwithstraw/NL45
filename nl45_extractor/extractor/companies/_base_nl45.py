"""
Base extraction utilities for NL-45 (Grievance Disposal).

Handles two observed PDF table layouts:

  Standard 9-column (Bajaj, Chola MS):
    col 0  sl_no
    col 1  particulars (row label)
    col 2  opening_balance
    col 3  additions
    col 4  fully_accepted        ─┐ Complaints Resolved
    col 5  partial_accepted       │
    col 6  rejected              ─┘
    col 7  pending_eoq
    col 8  total_registered_ytd

  Extended 10-column (New India — extra "Resolved with no option selected"):
    cols 0-6  same as above
    col 7  resolved_no_option     ← skipped (not in data model)
    col 8  pending_eoq
    col 9  total_registered_ytd

Benchmark row location — two variants:
  Separate table (Bajaj):  3-column table with row numbers 2-7 in col 0
  Embedded (New India, Chola): rows inside the status table after the "Total" row,
    with a digit 2-7 in col 0 and value in col 2
"""

import logging
import re
from typing import List, Optional, Tuple

from config.settings import BENCHMARK_ROW_MAP, BENCHMARK_VALUE_COL, get_status_column_indices
from config.row_registry import resolve_row, should_skip
from extractor.models import NL45StatusData, NL45BenchmarkData
from extractor.normaliser import clean_number, normalise_text

logger = logging.getLogger(__name__)


def is_status_table(table: List[list]) -> bool:
    """Return True if this pdfplumber table is the complaint status grid (Table 1)."""
    if len(table) < 4:
        return False
    # Must have 9 or 10 columns
    ncols = len(table[0])
    if ncols < 9:
        return False
    # Header rows must contain known NL-45 keywords
    # Scan first 10 rows as some companies have large header blocks (e.g. Raheja QBE)
    flat = " ".join(str(c or "") for row in table[:10] for c in row).upper()
    
    # Check for keywords, including common typo variants
    has_form_title = re.search(r"GR[IE]{2}VANCE\s+DISPOSAL", flat)
    has_header_labels = "OPENING BALANCE" in flat or "PARTICULARS" in flat
    
    return bool(has_form_title or has_header_labels)


def is_benchmark_table(table: List[list]) -> bool:
    """
    Return True if this table contains standalone benchmark rows (col0 = '2'-'7').

    Accepts any column count ≥ 3 to handle companies like Narayana Health that pack
    benchmark rows into an 8-col table alongside the duration section.
    Value is always read from col2 (same as Bajaj's 3-col layout).
    """
    if len(table) < 3:
        return False
    if not all(len(row) >= 3 for row in table if row):
        return False
    first_col_vals = {str(row[0] or "").strip() for row in table if row}
    return bool(first_col_vals & {"2", "3", "4", "5"})


def _is_benchmark_row(row: list) -> bool:
    """Return True if this row inside a status table is a benchmark metric row."""
    if not row or len(row) < 3:
        return False
    key = str(row[0] or "").strip()
    return key in BENCHMARK_ROW_MAP


def extract_status_table(table: List[list]) -> Tuple[NL45StatusData, Optional[NL45BenchmarkData]]:
    """
    Parse a status table into (NL45StatusData, NL45BenchmarkData | None).

    Single pass over all rows:
      - Skips header / section-header / footnote rows
      - Maps complaint-type rows to canonical keys
      - Collects embedded benchmark rows (if present) into NL45BenchmarkData

    Returns benchmark as None if no embedded benchmark rows were found
    (caller will then look for a separate benchmark table).
    """
    status = NL45StatusData()
    bm_fields: dict = {}

    ncols = max(len(r) for r in table if r)
    col_map = get_status_column_indices(ncols)

    for row in table:
        if not row:
            continue

        col0 = str(row[0] or "").strip()

        # Row 8 in NL-45 always marks the Duration wise Pending Status section — stop here
        # to prevent duration "Total Number of Complaints" from overwriting the complaint Total
        if col0 == "8":
            break

        # Embedded benchmark row (digit 2-7 in col 0, value in col 2)
        if _is_benchmark_row(row):
            row_num = str(row[0] or "").strip()
            field_name = BENCHMARK_ROW_MAP[row_num]
            val = clean_number(row[BENCHMARK_VALUE_COL] if len(row) > BENCHMARK_VALUE_COL else None)
            bm_fields[field_name] = val
            logger.debug(f"  embedded benchmark {field_name} = {val}")
            continue

        if len(row) < 9:
            continue

        # Use only the first line of the cell — "Others" rows often contain multi-line
        # sub-item descriptions like "(i) Claim related" that would match wrong types.
        raw_label = str(row[1] or "").split('\n')[0].strip()
        
        # Strip common sub-item prefixes like "a) ", "(i) ", "i) " to help matching
        raw_label = re.sub(r'^[a-z0-9\(\)]+[\)\.]\s*', '', raw_label, flags=re.IGNORECASE).strip()
        
        if not raw_label:
            continue

        if should_skip(raw_label):
            logger.debug(f"  SKIP: '{raw_label[:60]}'")
            continue

        complaint_type = resolve_row(raw_label, normalise_text)
        if complaint_type is None:
            logger.debug(f"  UNMATCHED: '{raw_label[:60]}'")
            continue

        # Don't overwrite — first occurrence wins.
        # Prevents AIC's Krishi sub-section rows (e.g. "(i) Claims") from overwriting the
        # already-captured standard complaint types and Sub Total.
        if complaint_type in status.data:
            logger.debug(f"  SKIP (already set): '{raw_label[:60]}' → {complaint_type}")
            continue

        metrics: dict = {}
        for col_idx, metric_key in col_map.items():
            raw_val = row[col_idx] if col_idx < len(row) else None
            metrics[metric_key] = clean_number(raw_val)

        status.data[complaint_type] = metrics
        logger.debug(f"  {complaint_type}: {metrics}")

    bm = None
    if bm_fields:
        bm = NL45BenchmarkData(**{k: v for k, v in bm_fields.items()
                                  if hasattr(NL45BenchmarkData, k) or k in NL45BenchmarkData.__dataclass_fields__})

    return status, bm


def extract_benchmark_table(table: List[list]) -> NL45BenchmarkData:
    """Parse a standalone 3-column benchmark table (Bajaj layout)."""
    bm = NL45BenchmarkData()
    for row in table:
        if not row or len(row) < 3:
            continue
        row_num = str(row[0] or "").strip()
        field_name = BENCHMARK_ROW_MAP.get(row_num)
        if field_name is None:
            continue
        val = clean_number(row[BENCHMARK_VALUE_COL])
        setattr(bm, field_name, val)
        logger.debug(f"  benchmark {field_name} = {val}")
    return bm


def find_nl45_tables(all_tables: List[List[list]]) -> Tuple[Optional[list], Optional[list]]:
    """
    Scan all tables on a page and return (status_table, standalone_benchmark_table).
    Either may be None. The embedded benchmark (if any) is extracted inside
    extract_status_table(), not returned here.
    """
    status_tbl = None
    benchmark_tbl = None

    for tbl in all_tables:
        if status_tbl is None and is_status_table(tbl):
            status_tbl = tbl
        elif benchmark_tbl is None and is_benchmark_table(tbl):
            benchmark_tbl = tbl

    return status_tbl, benchmark_tbl
