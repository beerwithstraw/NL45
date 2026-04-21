"""
Dedicated NL-45 parser for Aditya Birla Health Insurance.

Differences from the generic parser:
  1. 11-column table layout: col 0 = section row num, col 1 = S No. (a/b/c),
     col 2 = Particulars (complaint type label), cols 3-9 = metrics.
     Generic parser reads label from col 1 — here it must come from col 2.
  2. Benchmarks in a separate table (rows with col 1 = "2"-"7").
"""

import logging
from pathlib import Path

import pdfplumber

from config.company_registry import COMPANY_DISPLAY_NAMES
from config.row_registry import resolve_row, should_skip
from config.settings import BENCHMARK_ROW_MAP
from extractor.models import NL45Extract, NL45StatusData, NL45BenchmarkData
from extractor.normaliser import clean_number, normalise_text

logger = logging.getLogger(__name__)

# 11-col layout: label at col 2, metrics at cols 3-9
_COL_MAP_11 = {
    3: "opening_balance",
    4: "additions",
    5: "fully_accepted",
    6: "partial_accepted",
    7: "rejected",
    8: "pending_eoq",
    9: "total_registered_ytd",
}
_BENCHMARK_VALUE_COL_11 = 3  # value is in col 3 for the 11-col benchmark sub-table


def parse_aditya_birla(pdf_path: str, company_key: str,
                       quarter: str = "", year: str = "") -> NL45Extract:
    company_name = COMPANY_DISPLAY_NAMES.get(company_key, "Aditya Birla Health Insurance Co. Limited")
    extract = NL45Extract(
        source_file=Path(pdf_path).name,
        company_key=company_key,
        company_name=company_name,
        form_type="NL45",
        quarter=quarter,
        year=year,
    )

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for tbl in tables:
                    if not tbl or len(tbl[0]) < 10:
                        continue
                    status, bm = _parse_aditya_birla_table(tbl)
                    if status.data:
                        extract.status_data = status
                        if bm:
                            extract.benchmark_data = bm
                        break
                # Also check any table for benchmark rows (they live in the
                # 11-col combined table for Aditya Birla, not a separate 3-col table)
                if extract.status_data and extract.benchmark_data is None:
                    for tbl in tables:
                        if not tbl:
                            continue
                        bm = _parse_benchmark_table(tbl)
                        if bm:
                            extract.benchmark_data = bm
                            break
                if extract.status_data:
                    break
    except Exception as e:
        logger.error(f"Failed to parse {pdf_path}: {e}", exc_info=True)
        extract.extraction_errors.append(str(e))
        return extract

    if not extract.status_data or not extract.status_data.data:
        extract.extraction_warnings.append("No complaint status data extracted")
    else:
        logger.info(f"Extraction complete: {len(extract.status_data.data)} complaint types")

    return extract


def _parse_aditya_birla_table(table):
    status = NL45StatusData()
    bm = NL45BenchmarkData()
    found_bm = False

    for row in table:
        if not row or len(row) < 10:
            continue

        col0 = str(row[0] or "").strip()
        col1 = str(row[1] or "").strip()

        # Stop at Duration wise Pending Status section
        if col0 == "8":
            break

        # Embedded benchmark rows: digit 2-7 in col 1
        if col1 in BENCHMARK_ROW_MAP:
            field_name = BENCHMARK_ROW_MAP[col1]
            val = clean_number(row[_BENCHMARK_VALUE_COL_11] if len(row) > _BENCHMARK_VALUE_COL_11 else None)
            setattr(bm, field_name, val)
            found_bm = True
            continue

        # Label is at col 2 (Particulars), not col 1
        raw_label = str(row[2] or "").strip()
        if not raw_label or should_skip(raw_label):
            continue

        complaint_type = resolve_row(raw_label, normalise_text)
        if not complaint_type:
            continue

        metrics = {}
        for col_idx, metric_key in _COL_MAP_11.items():
            raw_val = row[col_idx] if col_idx < len(row) else None
            metrics[metric_key] = clean_number(raw_val)

        status.data[complaint_type] = metrics
        logger.debug(f"  {complaint_type}: {metrics}")

    return status, bm if found_bm else None


def _parse_benchmark_table(table):
    bm = NL45BenchmarkData()
    found = False
    for row in table:
        if not row or len(row) < 3:
            continue
        row_num = str(row[1] or "").strip()
        field_name = BENCHMARK_ROW_MAP.get(row_num)
        if field_name is None:
            continue
        if getattr(bm, field_name) is not None:  # first-wins: intermediaries block won't overwrite
            continue
        val = clean_number(row[_BENCHMARK_VALUE_COL_11] if len(row) > _BENCHMARK_VALUE_COL_11 else None)
        setattr(bm, field_name, val)
        found = True
    return bm if found else None
