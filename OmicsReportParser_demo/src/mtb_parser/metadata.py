"""Sample metadata from the report cover page.

The cover page contains (as plain lines, no label/value structure):

    Institut für Medizinische
    Bioinformatik und Systemmedizin
    Breisacher Straße 153
    79110 Freiburg
    Bericht zum Whole Genome Sequencing für
    das molekulare Tumorboard:
    MV26-32173
    2026-09-26
    Analyseergebnisse auf einen Blick

Values are kept exactly as printed (D3).
"""

from __future__ import annotations

import re

from .geometry import group_lines

_SAMPLE_RE = re.compile(r"^[A-Z]{2,4}\d{2}-\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def extract_metadata(words: list) -> dict:
    """Extract cover-page metadata from page-1 words."""
    meta: dict = {"sample_id": None, "report_date": None}
    for ln in group_lines(words):
        if ln.y0 > 300:
            break
        t = ln.text.strip()
        if meta["sample_id"] is None and _SAMPLE_RE.match(t):
            meta["sample_id"] = t
        elif meta["report_date"] is None and _DATE_RE.match(t):
            meta["report_date"] = t
    return meta
