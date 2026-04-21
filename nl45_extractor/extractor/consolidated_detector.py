"""
consolidated_detector.py — finds the NL-45 page range in a consolidated PDF.

Detection strategy:
  START: first page where >= min_matches NL-45 keywords appear
  END:   page before the next form header, or last page of PDF

NL-45 is a single-page form.
"""

import re
import logging
import tempfile
import os
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "GRIEVANCE DISPOSAL",
    "Opening Balance",       # appears in data table header — NOT in TOC pages
    "Sl No.",                # appears in data table header — NOT in TOC pages
]
DEFAULT_MIN_MATCHES = 2

FORM_HEADER_PATTERN = re.compile(r"FORM\s+NL[-\s]?(\d+)", re.IGNORECASE)


def _page_keyword_count(text: str, keywords: List[str]) -> int:
    text_upper = text.upper()
    return sum(1 for kw in keywords if kw.upper() in text_upper)


def find_nl45_pages(
    pdf_path: str,
    keywords: Optional[List[str]] = None,
    min_matches: int = DEFAULT_MIN_MATCHES,
) -> Optional[Tuple[int, int]]:
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not available")
        return None

    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    try:
        with pdfplumber.open(pdf_path) as pdf:
            n_pages = len(pdf.pages)
            page_texts = []
            for page in pdf.pages:
                try:
                    page_texts.append(page.extract_text() or "")
                except Exception:
                    page_texts.append("")

        start_page = None
        for i, text in enumerate(page_texts):
            if _page_keyword_count(text, keywords) >= min_matches:
                start_page = i
                break

        if start_page is None:
            logger.warning(f"NL-45 section not found in: {pdf_path}")
            return None

        end_page = n_pages - 1
        for i in range(start_page + 1, n_pages):
            matches = FORM_HEADER_PATTERN.findall(page_texts[i])
            non_nl45 = [m for m in matches if m != "45"]
            if non_nl45:
                end_page = i - 1
                break

        logger.info(
            f"NL-45 found at pages {start_page}-{end_page} "
            f"(0-indexed) in {os.path.basename(pdf_path)}"
        )
        return (start_page, end_page)

    except Exception as e:
        logger.error(f"Error scanning consolidated PDF {pdf_path}: {e}")
        return None


def extract_nl45_to_temp(pdf_path: str, start_page: int, end_page: int) -> Optional[str]:
    try:
        import pypdf
    except ImportError:
        try:
            import PyPDF2 as pypdf
        except ImportError:
            logger.error("pypdf or PyPDF2 not available")
            return None

    try:
        reader = pypdf.PdfReader(pdf_path)
        writer = pypdf.PdfWriter()
        for page_num in range(start_page, end_page + 1):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="nl45_extract_")
        with open(tmp.name, "wb") as f:
            writer.write(f)
        return tmp.name

    except Exception as e:
        logger.error(f"Error extracting pages from {pdf_path}: {e}")
        return None
