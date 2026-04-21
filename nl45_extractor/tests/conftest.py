"""pytest configuration — adds nl45_extractor/ to sys.path."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BAJAJ_PDF = os.path.expanduser(
    "~/Desktop/Forms/Fy2026/Q3/NL45/NL45_BajajGeneral.pdf"
)
