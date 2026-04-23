"""
Dedicated NL-45 parser for ICICI Lombard General Insurance Co. Ltd.

Differences from the generic parser:
  1. Handles Sl No prefixes (a, b, c) in the status table.
  2. Picks up benchmark metrics from Table 1 (8 columns).
"""

import logging
import re
from pathlib import Path

import pdfplumber

from config.company_registry import COMPANY_DISPLAY_NAMES
from config.row_registry import resolve_row, should_skip
from config.settings import BENCHMARK_ROW_MAP, BENCHMARK_VALUE_COL, get_status_column_indices
from extractor.models import NL45Extract, NL45StatusData, NL45BenchmarkData
from extractor.normaliser import clean_number, normalise_text

logger = logging.getLogger(__name__)


def parse_icici_lombard(pdf_path: str, company_key: str,
                        quarter: str = "", year: str = "") -> NL45Extract:
    company_name = COMPANY_DISPLAY_NAMES.get(company_key, "ICICI Lombard General Insurance")
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
                all_tables = page.extract_tables()
                if not all_tables:
                    continue

                for tbl in all_tables:
                    if not tbl:
                        continue
                    
                    ncols = len(tbl[0])
                    
                    # 1. Status Table (usually 9 columns)
                    if ncols >= 9 and _is_icici_status_table(tbl):
                        status_data = _extract_icici_status(tbl)
                        if status_data and status_data.data:
                            extract.status_data = status_data
                            logger.info(f"  Status data extracted ({len(status_data.data)} rows)")

                    # 2. Benchmark Table (usually 8 columns in ICICI)
                    elif ncols >= 3 and _is_icici_benchmark_table(tbl):
                        benchmark_data = _extract_icici_benchmark(tbl)
                        if benchmark_data:
                            extract.benchmark_data = benchmark_data
                            logger.info("  Benchmark data extracted")

                if extract.status_data:
                    break  # Found the main table

    except Exception as e:
        logger.error(f"Failed to parse {pdf_path}: {e}", exc_info=True)
        extract.extraction_errors.append(str(e))
        return extract

    if not extract.status_data or not extract.status_data.data:
        extract.extraction_warnings.append("No complaint status data extracted")
    
    if not extract.benchmark_data:
        extract.extraction_warnings.append("Benchmark table not found")

    return extract


def _is_icici_status_table(table):
    flat = " ".join(str(c or "") for row in table[:5] for c in row).upper()
    return "GRIEVANCE DISPOSAL" in flat and ("OPENING BALANCE" in flat or "PARTICULARS" in flat)


def _is_icici_benchmark_table(table):
    first_col_vals = {str(row[0] or "").strip() for row in table if row}
    return bool(first_col_vals & {"2", "3", "4", "5"})


def _extract_icici_status(table):
    status = NL45StatusData()
    ncols = max(len(r) for r in table if r)
    col_map = get_status_column_indices(ncols)

    for row in table:
        if not row or len(row) < 9:
            continue

        col0 = str(row[0] or "").strip()
        # Duration section starts at row 8
        if col0 == "8" or "DURATION WISE" in str(row[1] or "").upper():
            break

        raw_label = str(row[1] or "").split('\n')[0].strip()
        # Strip prefixes like "a) ", "b) "
        raw_label = re.sub(r'^[a-z0-9\(\)]+[\)\.]\s*', '', raw_label, flags=re.IGNORECASE).strip()
        
        if not raw_label or should_skip(raw_label):
            continue

        complaint_type = resolve_row(raw_label, normalise_text)
        if not complaint_type or complaint_type in status.data:
            continue

        metrics = {}
        for col_idx, metric_key in col_map.items():
            raw_val = row[col_idx] if col_idx < len(row) else None
            metrics[metric_key] = clean_number(raw_val)

        status.data[complaint_type] = metrics
    
    return status


def _extract_icici_benchmark(table):
    bm = NL45BenchmarkData()
    found = False
    for row in table:
        if not row or len(row) < 3:
            continue
        key = str(row[0] or "").strip()
        if key in BENCHMARK_ROW_MAP:
            field = BENCHMARK_ROW_MAP[key]
            val = clean_number(row[2]) # Benchmark value is usually in col 2
            setattr(bm, field, val)
            found = True
    return bm if found else None
