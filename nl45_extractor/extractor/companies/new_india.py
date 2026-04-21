"""
Dedicated NL-45 parser for The New India Assurance Co. Ltd.

Differences from the generic parser:
  1. 10-column table layout (extra "Resolved with no option selected" col at index 7)
  2. Benchmark rows embedded at the bottom of TABLE 1 (rows 14-19), not a separate table
  3. Duration-wise rows also embedded in TABLE 1 (rows 20-26) — must stop before these
     to avoid the duration "Total Number of Complaints" row overwriting the complaint Total

Stop condition: row col[0] == "8" signals the Duration wise Pending Status section.
"""

import logging
from pathlib import Path

import pdfplumber

from config.company_registry import COMPANY_DISPLAY_NAMES
from config.row_registry import resolve_row, should_skip
from config.settings import BENCHMARK_ROW_MAP, BENCHMARK_VALUE_COL, get_status_column_indices
from extractor.models import NL45Extract, NL45StatusData, NL45BenchmarkData
from extractor.normaliser import clean_number, normalise_text

logger = logging.getLogger(__name__)


def parse_new_india(pdf_path: str, company_key: str,
                    quarter: str = "", year: str = "") -> NL45Extract:
    company_name = COMPANY_DISPLAY_NAMES.get(company_key, "The New India Assurance Company")
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
                    if not tbl or len(tbl[0]) < 9:
                        continue
                    status, bm = _parse_new_india_table(tbl)
                    if status.data:
                        extract.status_data = status
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


def _parse_new_india_table(table):
    status = NL45StatusData()
    bm = NL45BenchmarkData()
    found_bm = False

    ncols = max(len(r) for r in table if r)
    col_map = get_status_column_indices(ncols)

    for row in table:
        if not row:
            continue

        col0 = str(row[0] or "").strip()

        # Stop: row 8 marks the Duration wise Pending Status section
        if col0 == "8":
            break

        # Benchmark rows: digit 2-7 in col 0
        if col0 in BENCHMARK_ROW_MAP:
            field_name = BENCHMARK_ROW_MAP[col0]
            val = clean_number(row[BENCHMARK_VALUE_COL] if len(row) > BENCHMARK_VALUE_COL else None)
            setattr(bm, field_name, val)
            found_bm = True
            logger.debug(f"  benchmark {field_name} = {val}")
            continue

        if len(row) < 9:
            continue

        raw_label = str(row[1] or "").strip()
        if not raw_label or should_skip(raw_label):
            continue

        complaint_type = resolve_row(raw_label, normalise_text)
        if not complaint_type:
            continue

        metrics = {}
        for col_idx, metric_key in col_map.items():
            raw_val = row[col_idx] if col_idx < len(row) else None
            metrics[metric_key] = clean_number(raw_val)

        status.data[complaint_type] = metrics
        logger.debug(f"  {complaint_type}: {metrics}")

    return status, bm if found_bm else None
