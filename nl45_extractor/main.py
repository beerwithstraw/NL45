"""
main.py — Quick single-file extraction entry point for NL-45.

Usage (from nl45_extractor/ directory):
  python3 main.py <pdf_path> <company_key> [--quarter Q3] [--year 202526]
  python3 main.py ~/Desktop/Forms/Fy2026/Q3/NL45/NL45_BajajGeneral.pdf bajaj_allianz --quarter Q3 --year 202526
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractor.parser import parse_pdf
from validation.checks import run_validations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(description="NL-45 Single-File Extraction")
    parser.add_argument("pdf_path", help="Path to the NL-45 PDF")
    parser.add_argument("company_key", help="Company key (e.g. bajaj_allianz)")
    parser.add_argument("--quarter", default="Q3")
    parser.add_argument("--year", default="202526")
    parser.add_argument("--output", default=None, help="Output XLSX path")
    args = parser.parse_args()

    pdf_path = os.path.expanduser(args.pdf_path)
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    extract = parse_pdf(pdf_path, args.company_key, args.quarter, args.year)

    print(f"\n=== NL-45 EXTRACTION RESULT ===")
    print(f"Company:  {extract.company_name}")
    print(f"Quarter:  {extract.quarter}  Year: {extract.year}")
    print(f"Source:   {extract.source_file}")

    if extract.status_data and extract.status_data.data:
        print(f"\nStatus Data ({len(extract.status_data.data)} complaint types):")
        print(f"  {'Complaint Type':<25} {'Opening':>10} {'Additions':>10} {'Fully Acc':>10} {'Partial':>10} {'Rejected':>10} {'Pending':>10} {'Total YTD':>12}")
        print("  " + "-" * 103)
        for ct, metrics in extract.status_data.data.items():
            o  = metrics.get("opening_balance")
            a  = metrics.get("additions")
            fa = metrics.get("fully_accepted")
            pa = metrics.get("partial_accepted")
            rj = metrics.get("rejected")
            pe = metrics.get("pending_eoq")
            ty = metrics.get("total_registered_ytd")
            def _fmt(v, w=10):
                return f"{v:>{w}.0f}" if v is not None else f"{'—':>{w}}"
            print(f"  {ct:<25} {_fmt(o)} {_fmt(a)} {_fmt(fa)} {_fmt(pa)} {_fmt(rj)} {_fmt(pe)} {_fmt(ty, 12)}")
    else:
        print("\nWARNING: No status data extracted!")

    if extract.benchmark_data:
        bm = extract.benchmark_data
        print(f"\nBenchmark Metrics:")
        print(f"  Policies previous year:           {bm.policies_prev_year}")
        print(f"  Claims previous year:             {bm.claims_prev_year}")
        print(f"  Policies current year:            {bm.policies_curr_year}")
        print(f"  Claims current year:              {bm.claims_curr_year}")
        print(f"  Policy complaints per 10K:        {bm.policy_complaints_per_10k}")
        print(f"  Claim complaints per 10K:         {bm.claim_complaints_per_10k}")

    if extract.extraction_warnings:
        print(f"\nWarnings: {extract.extraction_warnings}")
    if extract.extraction_errors:
        print(f"\nErrors: {extract.extraction_errors}")

    validation_results = run_validations([extract])
    if validation_results:
        print(f"\nValidation Results ({len(validation_results)} checks):")
        for r in validation_results:
            flag = "✓" if r.status == "PASS" else ("!" if r.status == "WARN" else "✗" if r.status == "FAIL" else "-")
            print(f"  [{flag}] {r.check_name:<40} {r.status:<5} {r.complaint_type:<25} {r.note or ''}")

    if args.output:
        from output.excel_writer import save_workbook
        out_path = os.path.expanduser(args.output)
        save_workbook([extract], out_path, stats={"files_processed": 1, "files_succeeded": 1, "files_failed": 0})
        print(f"\nOutput saved to: {out_path}")

    print()


if __name__ == "__main__":
    main()
