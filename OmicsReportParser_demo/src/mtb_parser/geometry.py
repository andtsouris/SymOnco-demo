"""Geometry layer: words, visual lines, rule bands, table fragments.

The reports are LaTeX (pdfTeX) documents using booktabs-style tables:
three horizontal rules per table (top / mid / bottom), no vertical rules,
no row rules.  Table fragments are therefore located by:

  * caption lines  ("Tabelle N: ...", possibly "(continued)"),
  * horizontal rule bands grouped by y,
  * top/mid/bottom triples (bands may be shared between stacked sub-tables),
  * per-x-range sub-tables for side-by-side tables (t07/t08).
"""

from __future__ import annotations

import re
from typing import Optional

from .models import RuleBand, RuleSegment, SubTable, TableFragment, TextLine, Word

# The page footer separator rule sits at y ~ 754.9 on every page; content above.
FOOTER_Y = 745.0

BAND_Y_TOL = 1.0          # segments within this y distance belong to one band
LINE_Y_TOL = 1.5          # words within this y0 distance belong to one visual line
X_MATCH_TOL = 6.0         # rule segments matching across top/mid/bottom bands
HEADER_H_MAX = 130.0      # max distance top->mid rule (10-col staggered headers reach ~120pt)
BODY_H_MAX = 700.0        # max distance mid->bottom rule (body area)
EXTRA_HDR_GAP_MIN = 5.0   # for stacked sub-tables sharing a band (t01)
EXTRA_HDR_GAP_MAX = 45.0
CAPTION_TOP_MAX = 90.0    # max distance caption line -> top rule


def extract_words(page) -> list[Word]:
    """Extract words in PDF stream order with per-character bold flags."""
    d = page.get_text("rawdict")
    words: list[Word] = []
    idx = 0

    def flush(chars: list[tuple[str, tuple, bool]]):
        nonlocal idx
        if not chars:
            return
        text = "".join(c[0] for c in chars)
        if not text.strip():
            return
        x0 = min(c[1][0] for c in chars)
        y0 = min(c[1][1] for c in chars)
        x1 = max(c[1][2] for c in chars)
        y1 = max(c[1][3] for c in chars)
        bold = any(c[2] for c in chars)
        words.append(Word(x0, y0, x1, y1, text, bold=bold, stream_idx=idx))
        idx += 1

    for block in d["blocks"]:
        if block.get("type") != 0:  # text blocks only
            continue
        for line in block["lines"]:
            current: list[tuple[str, tuple, bool]] = []
            for span in line["spans"]:
                bold = bool(span["flags"] & 16)  # bit 4 = bold
                for ch in span["chars"]:
                    c = ch["c"]
                    if c.isspace():
                        flush(current)
                        current = []
                    else:
                        current.append((c, ch["bbox"], bold))
            flush(current)
            current = []
    return words


def extract_rules(page) -> list[RuleSegment]:
    """Horizontal rule segments (excluding the page-footer rule)."""
    segs: list[RuleSegment] = []
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            p1, p2 = it[1], it[2]
            if abs(p1.y - p2.y) >= 0.5:  # not horizontal
                continue
            y = p1.y
            if y >= FOOTER_Y:
                continue
            x0, x1 = min(p1.x, p2.x), max(p1.x, p2.x)
            if x1 - x0 < 5.0:  # ignore dust
                continue
            segs.append(RuleSegment(y, x0, x1))
    return segs


def group_bands(segs: list[RuleSegment]) -> list[RuleBand]:
    """Group rule segments into bands by y coordinate."""
    bands: list[RuleBand] = []
    for seg in sorted(segs, key=lambda s: (s.y, s.x0)):
        if bands and abs(seg.y - bands[-1].y) <= BAND_Y_TOL:
            bands[-1].segments.append(seg)
        else:
            bands.append(RuleBand(seg.y, [seg]))
    for b in bands:
        b.segments.sort(key=lambda s: s.x0)
    return bands


def group_lines(words: list[Word], tol: float = LINE_Y_TOL) -> list[TextLine]:
    """Group words into visual lines by top coordinate (y0)."""
    lines: list[TextLine] = []
    for w in sorted(words, key=lambda w: (w.y0, w.x0)):
        if lines and w.y0 - lines[-1].y0 <= tol:
            lines[-1].words.append(w)
        else:
            lines.append(TextLine([w]))
    for ln in lines:
        ln.words.sort(key=lambda w: w.x0)
    return lines


_CAPTION_NUM = re.compile(r"^(\d+):?$")


def find_captions(lines: list[TextLine]) -> list[tuple[TextLine, int]]:
    """Find 'Tabelle N:' caption lines. Returns (line, table_number)."""
    out = []
    for ln in lines:
        if len(ln.words) >= 2 and ln.words[0].text == "Tabelle":
            m = _CAPTION_NUM.match(ln.words[1].text)
            if m:
                out.append((ln, int(m.group(1))))
    return out


def _seg_x_match(a: RuleSegment, b: RuleSegment, tol: float = X_MATCH_TOL) -> bool:
    return abs(a.x0 - b.x0) <= tol and abs(a.x1 - b.x1) <= tol


def _find_band_segment(bands: list[RuleBand], start_i: int, seg: RuleSegment,
                       dy_min: float, dy_max: float, window_upper: float
                       ) -> Optional[tuple[int, RuleSegment]]:
    """First band after start_i with a segment x-matching seg and y in range."""
    for j in range(start_i, len(bands)):
        b = bands[j]
        if b.y > window_upper:
            return None
        if b.y - seg.y < dy_min or b.y - seg.y > dy_max:
            continue
        for s in b.segments:
            if _seg_x_match(seg, s):
                return j, s
    return None


def words_in_region(words: list[Word], y0: float, y1: float,
                    x0: Optional[float] = None, x1: Optional[float] = None) -> list[Word]:
    out = []
    for w in words:
        if w.y_center <= y0 or w.y_center >= y1:
            continue
        if x0 is not None and (w.x_center < x0 - 2 or w.x_center > x1 + 2):
            continue
        out.append(w)
    return out


def _caption_text(all_lines: list[TextLine], cap_line: TextLine, top_y: float) -> str:
    """Caption text: from the caption line down to (excl.) the top rule.
    Includes wrapped caption lines and footnote lines (e.g. T23 '4* ...')."""
    parts = []
    for ln in all_lines:
        if ln.y0 < cap_line.y0 - 1 or ln.y0 >= top_y - 1:
            continue
        parts.append(ln)
    parts.sort(key=lambda ln: ln.y0)
    return " ".join(ln.text for ln in parts)


def find_fragments(page_no: int, words: list[Word],
                   bands: list[RuleBand]) -> list[TableFragment]:
    """Detect all table fragments (captions + sub-tables) on a page."""
    all_lines = group_lines(words)
    captions = find_captions(all_lines)
    fragments: list[TableFragment] = []

    for ci, (cap_line, number) in enumerate(captions):
        # top band: first band below the caption line
        top_i = None
        for j, b in enumerate(bands):
            if b.y > cap_line.y1 + 1 and b.y - cap_line.y1 <= CAPTION_TOP_MAX:
                top_i = j
                break
        if top_i is None:
            # Caption without a rule triple below (e.g. TOC mentions): skip.
            continue

        # window upper bound: top band of the *next* caption, else page bottom
        window_upper = FOOTER_Y
        for next_line, _ in captions[ci + 1:]:
            for j, b in enumerate(bands):
                if b.y > next_line.y1 + 1:
                    window_upper = min(window_upper, b.y)
                    break
            break

        top_band = bands[top_i]
        sub_tables: list[SubTable] = []

        for seg in top_band.segments:
            mid = _find_band_segment(bands, top_i + 1, seg, 5.0, HEADER_H_MAX, window_upper)
            if mid is None:
                continue
            mid_j, _mid_seg = mid
            bottom = _find_band_segment(bands, mid_j + 1, seg, 3.0, BODY_H_MAX, window_upper)
            bottom_y = _matching_bottom(bands, bottom[0], seg) if bottom else None
            sub_tables.append(SubTable(
                page_no=page_no, x0=seg.x0, x1=seg.x1,
                top_y=top_band.y, mid_y=bands[mid_j].y,
                bottom_y=bottom_y, table_number=number,
                is_continuation=False, caption_text="",
            ))

        # Stacked sub-tables sharing the previous bottom band (t01 pattern):
        # look for (mid, bottom) band pairs after the last bottom, with header
        # text between last_bottom and mid.
        if sub_tables and any(st.bottom_y for st in sub_tables):
            last_bottom = max(st.bottom_y for st in sub_tables if st.bottom_y)
            consumed_mid = {st.mid_y for st in sub_tables}
            consumed_bottom = {st.bottom_y for st in sub_tables if st.bottom_y}
            while last_bottom is not None:
                found = None
                for j, b in enumerate(bands):
                    if b.y <= last_bottom + EXTRA_HDR_GAP_MIN or b.y - last_bottom > EXTRA_HDR_GAP_MAX:
                        continue
                    if b.y in consumed_mid or b.y in consumed_bottom:
                        continue
                    if not any(_seg_x_match(s, ts) for s in b.segments for ts in top_band.segments):
                        continue
                    # header text required between last_bottom and b
                    hdr_words = words_in_region(words, last_bottom + 1, b.y - 1)
                    if len(hdr_words) < 2:
                        continue
                    # bottom band after mid
                    bottom = _find_band_segment(bands, j + 1, b.segments[0], 3.0, BODY_H_MAX, window_upper)
                    if bottom is None:
                        continue
                    bottom_band = bands[bottom[0]]
                    bseg = next((s for s in bottom_band.segments
                                 if _seg_x_match(s, b.segments[0])), None)
                    if bseg is None:
                        continue
                    found = (b, bottom_band, bseg)
                    break
                if found is None:
                    break
                mid_band, bottom_band, bseg = found
                for ts in top_band.segments:
                    if _seg_x_match(bseg, ts):
                        sub_tables.append(SubTable(
                            page_no=page_no, x0=ts.x0, x1=ts.x1,
                            top_y=last_bottom, mid_y=mid_band.y,
                            bottom_y=bottom_band.y, table_number=number,
                            is_continuation=False, caption_text="",
                        ))
                last_bottom = bottom_band.y
                consumed_mid.add(mid_band.y)
                consumed_bottom.add(bottom_band.y)

        if not sub_tables:
            continue

        sub_tables.sort(key=lambda st: (st.top_y, st.x0))
        is_cont = "(continued)" in _caption_text(all_lines, cap_line, top_band.y + 1)
        caption = _caption_text(all_lines, cap_line, top_band.y + 1)
        frag = TableFragment(page_no=page_no, table_number=number,
                             is_continuation=is_cont, caption_text=caption,
                             sub_tables=sub_tables)
        for st in frag.sub_tables:
            st.caption_text = caption
            st.is_continuation = is_cont
            st.header_words = words_in_region(words, st.top_y + 1, st.mid_y - 1, st.x0, st.x1)
            body_top = st.mid_y + 1
            body_bottom = st.bottom_y - 1 if st.bottom_y is not None else FOOTER_Y
            st.body_words = words_in_region(words, body_top, body_bottom, st.x0, st.x1)
        fragments.append(frag)

    fragments.sort(key=lambda f: (f.sub_tables[0].top_y, f.table_number))
    return fragments


def _matching_bottom(bands: list[RuleBand], band_idx: int, seg: RuleSegment) -> Optional[float]:
    """Return y of the band if it contains a segment x-matching seg."""
    for s in bands[band_idx].segments:
        if _seg_x_match(seg, s):
            return bands[band_idx].y
    return None


def find_orphan_continuation(page_no: int, words: list[Word], bands: list[RuleBand],
                             anchor_x: Optional[float], table_number: int
                             ) -> Optional[TableFragment]:
    """Detect continuation table rows sitting above the first rule band of a
    page, *without* a caption (observed: last row of a long table placed in the
    top margin above the next table's caption).

    The words are attributed to `table_number` (an open table from the previous
    page) only if at least one zone line starts near the table's anchor column.
    """
    if not bands or anchor_x is None:
        return None
    top = min(b.y for b in bands)
    zone = [w for w in words if 60.0 < w.y_center < top - 3.0]
    if not zone:
        return None
    lines = group_lines(zone)
    if any(ln.words and ln.words[0].text == "Tabelle" for ln in lines):
        return None  # real caption: handled by find_fragments
    start = None
    for ln in lines:
        if abs(ln.words[0].x0 - anchor_x) <= 12.0:
            start = ln.y0
            break
    if start is None:
        return None
    out_words = [w for w in zone if w.y_center >= start - 3.0]
    y_min = min(w.y0 for w in out_words)
    st = SubTable(
        page_no=page_no,
        x0=min(w.x0 for w in out_words) - 4.0,
        x1=max(w.x1 for w in out_words) + 4.0,
        top_y=y_min - 2.0, mid_y=y_min - 2.0, bottom_y=top,
        table_number=table_number, is_continuation=True,
        caption_text="(continued, no caption)",
        header_words=[], body_words=out_words,
    )
    return TableFragment(page_no=page_no, table_number=table_number,
                         is_continuation=True,
                         caption_text="(continued, no caption)",
                         sub_tables=[st])


def parse_page(page_no: int, page) -> tuple[list[Word], list[RuleBand], list[TableFragment]]:
    """Full geometry extraction for one page."""
    words = extract_words(page)
    bands = group_bands(extract_rules(page))
    fragments = find_fragments(page_no, words, bands)
    return words, bands, fragments
