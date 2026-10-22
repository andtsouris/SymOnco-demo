"""Logical row reconstruction and cell text assembly.

A logical row starts at a visual line that contains a word in the anchor column
(e.g. the ``Gen`` column of mutation tables).  All following visual lines without
an anchor word are continuation lines (wrapped cell content).

Cell text is assembled by joining the visual lines of a row that fall into the
column.  Line joining is wrap-aware:

* a line ending in ``e-``/``-`` followed by a digit joins without a space
  (scientific notation wrapped mid-token, e.g. ``2.1e-`` + ``04``),
* in the AA-change column, HGVS token fragments join without a space
  (``p.R162Sf`` + ``s*17`` -> ``p.R162Sfs*17``),
* otherwise a single space is inserted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .columns import ColumnLayout
from .geometry import LINE_Y_TOL, TextLine, Word, group_lines
from .models import ParseWarning

_AA_TOKEN = re.compile(r"[pNc][.\-_]?[A-Za-z0-9_\-*]+")


@dataclass
class Row:
    cells: list[list[Word]]  # column index -> words (visual line order preserved)
    lines: list[TextLine] = field(default_factory=list)

def row_hotspot(row: Row, column_names: list[str]) -> bool:
    """Hotspot = mutation row printed in bold font.

    Only the Gen / AA-Austausch cells are considered: other columns may be bold
    for unrelated reasons (e.g. pathway labels in t09/t15, failing QC values in t19).
    """
    cols = {"Gen": [], "AA-Austausch": []}
    for i, name in enumerate(column_names):
        if name in cols and i < len(row.cells):
            cols[name].extend(row.cells[i])
    words = [w for cell in cols.values() for w in cell]
    return any(w.bold for w in words) if words else False


def build_rows(body_words: list[Word], layout: ColumnLayout, anchor_col: int
               ) -> tuple[list[Row], list[ParseWarning]]:
    """Group body words into logical rows using the anchor column."""
    warnings: list[ParseWarning] = []
    if not body_words or layout.n_columns == 0:
        return [], warnings

    lines = group_lines(body_words, LINE_Y_TOL)
    rows: list[Row] = []
    for ln in lines:
        cols = {layout.assign(w.x0) for w in ln.words}
        if anchor_col in cols or not rows:
            cells: list[list[Word]] = [[] for _ in range(layout.n_columns)]
            for w in ln.words:
                cells[layout.assign(w.x0)].append(w)
            row = Row(cells, [ln])
            rows.append(row)
        else:
            rows[-1].lines.append(ln)
            for w in ln.words:
                rows[-1].cells[layout.assign(w.x0)].append(w)
    return rows, warnings


def _aa_fragment(s: str) -> bool:
    """True if s looks like (a prefix of) an HGVS protein token."""
    return bool(_AA_TOKEN.fullmatch(s))


def join_cell(words: list[Word], is_aa_column: bool = False) -> str:
    """Join the words of one cell (multiple visual lines) into cell text."""
    if not words:
        return ""
    lines = group_lines(words, LINE_Y_TOL)
    parts = [" ".join(w.text for w in sorted(ln.words, key=lambda w: w.x0)) for ln in lines]
    out = ""
    for p in parts:
        if not out:
            out = p
            continue
        sep = " "
        if (out.endswith("e-") or out.endswith("-")) and p[:1].isdigit():
            sep = ""
        elif is_aa_column and _aa_fragment(out) and _aa_fragment(out + p):
            sep = ""
        out += sep + p
    return re.sub(r"\s+", " ", out).strip()


def assemble_rows(rows: list[Row], column_names: list[str],
                  warnings: list[ParseWarning]) -> list[dict]:
    """Convert logical rows into dicts keyed by column name (empty -> "")."""
    out = []
    for row in rows:
        d: dict[str, str | bool | None] = {}
        for i, name in enumerate(column_names):
            if i < len(row.cells):
                d[name] = join_cell(row.cells[i], is_aa_column=(name == "AA-Austausch"))
            else:
                d[name] = ""
        d["hotspot"] = row_hotspot(row, column_names)
        out.append(d)
    return out
