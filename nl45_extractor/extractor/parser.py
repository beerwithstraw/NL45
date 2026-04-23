"""
NL-45 Generic Parser (Grievance Disposal).

NL-45 page layout (confirmed via pdfplumber on Bajaj Q3 FY2025-26):
  TABLE 0: title block — skipped
  TABLE 1: complaint status grid (9 cols) — extracted as NL45StatusData
  TABLE 2: benchmark/ratio metrics (3 cols) — extracted as NL45BenchmarkData
  TABLE 3: duration-wise pending — out of scope (ignored)

Output model: NL45Extract with status_data and benchmark_data populated.
"""

import logging
from pathlib import Path

import pdfplumber

from config.company_registry import COMPANY_DISPLAY_NAMES, DEDICATED_PARSER
from extractor.companies._base_nl45 import find_nl45_tables, extract_status_table, extract_benchmark_table
from extractor.models import NL45Extract

logger = logging.getLogger(__name__)


def parse_pdf(pdf_path: str, company_key: str, quarter: str = "", year: str = "") -> NL45Extract:
    """Main entry point — parses one NL-45 PDF."""
    logger.info(f"Parsing NL-45 PDF: {pdf_path} for company: {company_key}")

    company_name = COMPANY_DISPLAY_NAMES.get(company_key, str(company_key).title())

    dedicated_func_name = DEDICATED_PARSER.get(company_key)
    if dedicated_func_name:
        from extractor.companies import PARSER_REGISTRY
        dedicated_func = PARSER_REGISTRY.get(dedicated_func_name)
        if dedicated_func:
            logger.info(f"Routing to dedicated parser: {dedicated_func_name}")
            return dedicated_func(pdf_path, company_key, quarter, year)

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
            for pg_idx, page in enumerate(pdf.pages):
                all_tables = page.extract_tables()
                if not all_tables:
                    continue

                status_tbl, benchmark_tbl = find_nl45_tables(all_tables)

                if status_tbl is not None:
                    logger.debug(f"Page {pg_idx}: found status table ({len(status_tbl)} rows)")
                    extract.status_data, embedded_bm = extract_status_table(status_tbl)
                    if embedded_bm is not None:
                        extract.benchmark_data = embedded_bm
                        logger.debug(f"Page {pg_idx}: benchmark extracted from embedded rows")

                if benchmark_tbl is not None and extract.benchmark_data is None:
                    logger.debug(f"Page {pg_idx}: found standalone benchmark table ({len(benchmark_tbl)} rows)")
                    extract.benchmark_data = extract_benchmark_table(benchmark_tbl)

                if extract.status_data is not None and extract.status_data.data:
                    break  # NL-45 is a single-page form

    except Exception as e:
        logger.error(f"Failed to parse {pdf_path}: {e}", exc_info=True)
        extract.extraction_errors.append(str(e))
        return extract

    if extract.status_data is None or not extract.status_data.data:
        msg = "No complaint status data extracted"
        logger.warning(f"{msg}: {pdf_path}")
        extract.extraction_warnings.append(msg)
    else:
        n = len(extract.status_data.data)
        logger.info(f"Extraction complete: {n} complaint types extracted")

    if extract.benchmark_data is None:
        logger.warning(f"Benchmark table not found: {pdf_path}")
        extract.extraction_warnings.append("Benchmark table not found")

    return extract
