"""
Data models for the NL-45 extractor (Grievance Disposal).

NL45Extract contains two optional sub-objects:
  status_data   — the main complaint status grid (Table 1)
  benchmark_data — scalar benchmark/ratio metrics (Table 2)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class NL45StatusData:
    """
    Holds Table 1 — the complaint status grid.

    data[complaint_type][metric_key] = float | None
      complaint_type: canonical key from NL45_ROW_ORDER (e.g. "claim")
      metric_key:     one of STATUS_METRICS (e.g. "opening_balance")
    """
    data: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)


@dataclass
class NL45BenchmarkData:
    """Holds Table 2 — the six scalar benchmark/ratio metrics."""
    policies_prev_year:         Optional[float] = None
    claims_prev_year:           Optional[float] = None
    policies_curr_year:         Optional[float] = None
    claims_curr_year:           Optional[float] = None
    policy_complaints_per_10k:  Optional[float] = None
    claim_complaints_per_10k:   Optional[float] = None


@dataclass
class NL45Extract:
    """Top-level container for one extracted NL-45 PDF."""
    source_file: str
    company_key: str
    company_name: str
    form_type: str = "NL45"
    quarter: str = ""
    year: str = ""
    status_data:    Optional[NL45StatusData]    = None
    benchmark_data: Optional[NL45BenchmarkData] = None
    extraction_warnings: list = field(default_factory=list)
    extraction_errors:   list = field(default_factory=list)
