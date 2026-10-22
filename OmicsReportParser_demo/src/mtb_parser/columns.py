"""Column detection and word-to-column assignment.

Column left edges are seeded from *header* word start positions and kept only if
supported by body words (cells are left-aligned in these LaTeX tables).  This is
robust against multi-word header cells (e.g. ``VAF [%] (Coverage) Tumor``) and
against second words of body cells, which never appear in the header.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .geometry import LINE_Y_TOL, TextLine, Word, group_lines

EDGE_TOL = 2.0        # clustering tolerance for start-x positions
SUPPORT_TOL = 8.0     # body word start may deviate from header edge by this much


@dataclass
class ColumnLayout:
    edges: list[float]                      # sorted column left edges
    spans: list[tuple[float, float]]        # (min x0, max x1) per column (body words)

    @property
    def n_columns(self) -> int:
        return len(self.edges)

    def assign(self, x0: float) -> int:
        """Column index for a word starting at x0 (largest edge <= x0 + tol)."""
        idx = 0
        for i, e in enumerate(self.edges):
            if x0 >= e - EDGE_TOL:
                idx = i
        return idx

    @classmethod
    def from_edges(cls, edges: list[float], body_words: list) -> "ColumnLayout":
        """Layout from registry-seeded column edges (no support heuristic)."""
        layout = cls(sorted(edges), [(0.0, 0.0)] * len(edges))
        if not body_words:
            for i in range(len(edges)):
                layout.spans[i] = (edges[i], edges[i])
            return layout
        min_x = [float("inf")] * len(edges)
        max_x = [0.0] * len(edges)
        for w in body_words:
            i = layout.assign(w.x0)
            min_x[i] = min(min_x[i], w.x0)
            max_x[i] = max(max_x[i], w.x1)
        for i in range(len(edges)):
            layout.spans[i] = ((min_x[i], max_x[i]) if min_x[i] != float("inf")
                               else (edges[i], edges[i]))
        return layout


def _cluster(values: list[float], tol: float = EDGE_TOL) -> list[float]:
    """1-D clustering of x positions; returns cluster representatives."""
    out: list[float] = []
    for v in sorted(values):
        if out and v - out[-1] <= tol:
            continue  # keep first (leftmost) representative
        out.append(v)
    return out


def _gap_starts(header_words: list[Word], gap: float = 8.0) -> list[float]:
    """Header word start positions that start a new header cell: first word of
    the stream or a gap of more than `gap` pt from the previous word's end.
    (Multi-word header cells like 'Komplexe Biomarker' produce one start only.)
    """
    out: list[float] = []
    prev_x1: Optional[float] = None
    for w in sorted(header_words, key=lambda w: w.stream_idx):
        if prev_x1 is None or w.x0 - prev_x1 > gap:
            out.append(w.x0)
        prev_x1 = w.x1 if prev_x1 is None else max(prev_x1, w.x1)
    return out


def detect_columns(header_words: list[Word], body_words: list[Word],
                   body_lines: Optional[list[TextLine]] = None) -> ColumnLayout:
    """Detect column left edges for one sub-table.

    Edges = header word start-x clusters supported by body words.  An empty body
    yields no edges (no rows to reconstruct).
    """
    if not body_words:
        return ColumnLayout([], [])

    if body_lines is None:
        body_lines = group_lines(body_words, LINE_Y_TOL)
    n_lines = len(body_lines)

    # body line starts per x cluster (distinct visual lines); a line supports an
    # edge if a word starts near the edge (left-aligned) or lies fully inside the
    # column span (center/right-aligned values, e.g. small integers).
    def support(x: float, next_edge: Optional[float] = None) -> int:
        n = 0
        span_end = (next_edge - 2.0) if next_edge is not None else None
        for ln in body_lines:
            for w in ln.words:
                if abs(w.x0 - x) <= SUPPORT_TOL:
                    n += 1
                    break
                if (span_end is not None and w.x0 >= x - 2.0
                        and w.x1 <= span_end):
                    n += 1
                    break
        return n

    threshold = 1 if n_lines == 1 else max(2, math.ceil(0.3 * n_lines))
    header_starts = [w.x0 for w in header_words]
    candidates = _cluster(header_starts)
    supported = [(e, support(e, candidates[i + 1] if i + 1 < len(candidates) else None))
                 for i, e in enumerate(candidates) if
                 support(e, candidates[i + 1] if i + 1 < len(candidates) else None) >= threshold]
    if not supported:  # fallback: gap-start header cells with at least one body line hit
        supported = [(e, support(e)) for e in _gap_starts(header_words) if support(e) >= 1]
    # Deduplicate near-duplicates (multi-line header cells put 2nd/3rd words a few
    # pt right of the true edge): within 12 pt keep the higher-support / leftmost.
    supported.sort()
    edges: list[float] = []
    for e, s in supported:
        if edges and e - edges[-1] <= 12.0:
            keep_new = s > support(edges[-1])
            if keep_new:
                edges[-1] = e
            continue
        edges.append(e)
    if not edges:  # last resort: gap starts even without body support
        edges = _gap_starts(header_words)
    layout = ColumnLayout.from_edges(edges, body_words)
    return layout


def assign_words(words: list[Word], layout: ColumnLayout) -> dict[int, list[Word]]:
    """Assign words to columns (with nearest-span fallback for outliers)."""
    out: dict[int, list[Word]] = {i: [] for i in range(layout.n_columns)}
    for w in words:
        i = layout.assign(w.x0)
        # fallback: word left of the first edge -> nearest span by overlap
        if i == 0 and w.x0 < layout.edges[0] - EDGE_TOL:
            best, best_ov = 0, -1.0
            for j, (s0, s1) in enumerate(layout.spans):
                ov = max(0.0, min(w.x1, s1) - max(w.x0, s0))
                if ov > best_ov:
                    best, best_ov = j, ov
            i = best if best_ov > 0 else 0
        out[i].append(w)
    return out
