"""Report-level orchestration: stitch fragments, verify headers, assemble rows."""

from __future__ import annotations

import re

from . import columns as columns_mod
from . import geometry, header_check, rows as rows_mod
from .header_check import HeaderMatch
from .models import ParsedTable, ParseWarning
from .registry import SPEC_BY_NUMBER, TABLE_SPECS, TableSpec

W_TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
W_TABLE_EMPTY = "TABLE_EMPTY"
W_CONT_DRIFT = "CONTINUATION_HEADER_DRIFT"
W_SUBTABLE_UNEXPECTED = "SUBTABLE_UNEXPECTED"
W_COL_COUNT = "COLUMN_COUNT_DRIFT"
W_COL_MISSING = "COLUMN_MISSING"
W_CONT_NO_CAPTION = "CONTINUATION_WITHOUT_CAPTION"
W_ROW_ANOMALY = "ROW_ANOMALY"

EDGE_PAIR_TOL = 12.0


def _clean_title(frag) -> str:
    text = frag.caption_text
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^Tabelle\s+\d+:\s*", "", text)
    text = re.sub(r"\s*\(continued\)\s*", " ", text).strip()
    return text


def _build_layout(st, sub_headers: list[str], match: HeaderMatch,
                  table_id: str, page: int,
                  warns: list[ParseWarning]):
    """Column layout + column names for one sub-table.

    Primary path (registry-seeded): when every expected header matched the
    printed header row, the column left edges are exactly the first words of
    the matched header cells — no heuristic ambiguity, robust against staggered
    multi-line headers and center-aligned numeric cells.
    Fallback (heuristic): header words + body support detection.
    """
    left = header_check.header_left_edges(match, st.header_words)
    if all(e is not None for e in left):
        order = sorted(range(len(left)), key=lambda i: (left[i], i))
        edges = [left[i] for i in order]
        names = [sub_headers[i] for i in order]
        layout = columns_mod.ColumnLayout.from_edges(edges, st.body_words)
        return layout, names
    layout = columns_mod.detect_columns(st.header_words, st.body_words)
    names = _map_column_names(layout, sub_headers, match,
                              st.header_words, warns, page, table_id)
    return layout, names


def _map_column_names(layout, expected: list[str], match: HeaderMatch,
                      header_words, warns: list[ParseWarning],
                      page: int, table_id: str) -> list[str]:
    """Pair detected columns (edges) with expected headers.

    Positional when the counts agree (the common case); otherwise nearest
    expected column-left-edge pairing with warnings.
    """
    edges = layout.edges
    if len(edges) == len(expected):
        return list(expected)
    left = header_check.header_left_edges(match, header_words)
    names: list[str] = []
    used: set[int] = set()
    for e in edges:
        best, bd = None, 1e9
        for i, le in enumerate(left):
            if le is None or i in used:
                continue
            d = abs(e - le)
            if d < bd:
                bd, best = d, i
        if best is not None and bd <= EDGE_PAIR_TOL:
            names.append(expected[best])
            used.add(best)
        else:
            names.append(f"_col{len(names)}")
    if len(edges) != len(expected):
        warns.append(ParseWarning(
            W_COL_COUNT,
            f"column count differs: expected {len(expected)}, detected {len(edges)} "
            f"(Tabelle page {page})",
            table_id=table_id, page=page,
            expected=str(len(expected)), found=str(len(edges))))
    for i, exp in enumerate(expected):
        if i not in used:
            warns.append(ParseWarning(
                W_COL_MISSING,
                f"no detected column for expected header {exp!r} (page {page})",
                table_id=table_id, page=page, expected=exp))
    return names


def _anchor_index(spec: TableSpec, names: list[str],
                  sub_headers: list[str] | None) -> int:
    if spec.sub_tables:
        anchor_name = sub_headers[0] if sub_headers else None
    else:
        anchor_name = spec.expected_headers[spec.anchor]
    if anchor_name in names:
        return names.index(anchor_name)
    return 0


def _parse_numbered(spec: TableSpec, fraglist: list[tuple[int, object]]) -> ParsedTable:
    warns: list[ParseWarning] = []
    title = ""
    all_rows: list[dict] = []
    pages: list[int] = []
    first_header_text: dict[int, str] = {}

    if not fraglist:
        warns.append(ParseWarning(
            W_TABLE_NOT_FOUND,
            f"Tabelle {spec.number} not found in report",
            table_id=spec.table_id))
    else:
        output_cols = list(spec.output_columns or spec.expected_headers)
        if spec.hotspot and "hotspot" not in output_cols:
            output_cols = output_cols + ["hotspot"]
        last_layouts: dict[int, tuple] = {}  # sub-table idx -> (layout, names)

        for idx, (page, frag) in enumerate(fraglist):
            is_cont = idx > 0
            if not is_cont:
                title = _clean_title(frag)
            pages.append(page)
            for si, st in enumerate(frag.sub_tables):
                if spec.sub_tables:
                    if si >= len(spec.sub_tables):
                        warns.append(ParseWarning(
                            W_SUBTABLE_UNEXPECTED,
                            f"unexpected sub-table {si} in "
                            f"Tabelle {spec.number} (page {page})",
                            table_id=spec.table_id, page=page))
                        continue
                    sub = spec.sub_tables[si]
                    sub_headers, block, cmap = sub.headers, sub.block, sub.column_map
                else:
                    sub_headers, block, cmap = spec.expected_headers, None, None

                if not st.header_words:
                    # continuation rows without caption/header (top-margin rows):
                    # reuse the column layout of the previous fragment.
                    if si not in last_layouts:
                        warns.append(ParseWarning(
                            W_ROW_ANOMALY,
                            f"Tabelle {spec.number}: caption-less rows on page "
                            f"{page} without a previous layout (skipped)",
                            table_id=spec.table_id, page=page))
                        continue
                    layout, names = last_layouts[si]
                else:
                    hdr_text = " ".join(w.text for w in st.header_words)
                    if is_cont:
                        if si not in first_header_text:
                            first_header_text[si] = hdr_text
                        elif hdr_text != first_header_text[si]:
                            warns.append(ParseWarning(
                                W_CONT_DRIFT,
                                f"continuation header differs (page {page})",
                                table_id=spec.table_id, page=page,
                                expected=first_header_text[si], found=hdr_text))
                    match = header_check.check_headers(
                        st.header_words, sub_headers, page, spec.table_id, is_cont)
                    warns.extend(match.warnings)
                    layout, names = _build_layout(st, sub_headers, match,
                                                  spec.table_id, page, warns)
                    last_layouts[si] = (layout, names)

                if not st.body_words:
                    continue  # empty fragment: header validated, no rows/columns
                anchor = _anchor_index(spec, names, sub_headers)
                lrows, _ = rows_mod.build_rows(st.body_words, layout, anchor)
                drows = rows_mod.assemble_rows(lrows, names, [])
                for r in drows:
                    rd: dict = {c: None for c in output_cols}
                    for k, v in r.items():
                        if k == "hotspot":
                            if spec.hotspot:
                                rd["hotspot"] = v
                            continue
                        target = cmap.get(k, k) if cmap else k
                        if target in rd:
                            rd[target] = v if v != "" else None
                        else:  # extra column not in schema: keep verbatim (D5)
                            rd[f"_{k}"] = v if v != "" else None
                    if block is not None:
                        rd["block"] = block
                    all_rows.append(rd)

    if spec.forward_fill and all_rows:
        _forward_fill(all_rows, spec.forward_fill)

    if not all_rows:
        warns.append(ParseWarning(
            W_TABLE_EMPTY,
            f"Tabelle {spec.number} has no data rows",
            table_id=spec.table_id))

    return ParsedTable(
        table_id=spec.table_id,
        slug=spec.slug,
        table_number=spec.number,
        title=title or spec.title_fallback,
        columns=output_cols if fraglist else list(spec.output_columns or spec.expected_headers),
        rows=all_rows,
        pages=pages,
        warnings=warns,
        expected_headers=list(spec.expected_headers),
    )


def _forward_fill(all_rows: list[dict], cols: tuple[str, ...]) -> None:
    """Forward-fill merged category cells ('' or '.' = ditto, e.g. t02 Kategorie)."""
    last: dict[str, str | None] = {c: None for c in cols}
    for r in all_rows:
        for c in cols:
            v = r.get(c)
            if v is None or v == ".":
                if last[c] is not None:
                    r[c] = last[c]
            else:
                last[c] = v


def _open_anchor_x(frag, spec: TableSpec | None) -> float | None:
    """x0 of the anchor column of a table's last sub-table (for orphan rows)."""
    st = frag.sub_tables[0]
    if not st.header_words:
        return None
    layout = columns_mod.detect_columns(st.header_words, st.body_words)
    if not layout.edges:
        return None
    anchor = 0
    if spec is not None and not spec.sub_tables:
        anchor = min(spec.anchor, len(layout.edges) - 1)
    return layout.edges[anchor]


def parse_tables(page_data: list[tuple]) -> list[ParsedTable]:
    """page_data: list of (page_no, words, bands, fragments) in page order."""
    by_number: dict[int, list[tuple[int, object]]] = {}
    open_table: tuple[int, float] | None = None  # (number, anchor_x)
    orphan_notes: list[ParseWarning] = []
    for page_no, words, bands, frags in page_data:
        if open_table is not None:
            orph = geometry.find_orphan_continuation(
                page_no, words, bands, open_table[1], open_table[0])
            if orph is not None:
                by_number.setdefault(orph.table_number, []).append((page_no, orph))
                orph_spec = SPEC_BY_NUMBER.get(orph.table_number)
                orphan_notes.append(ParseWarning(
                    W_CONT_NO_CAPTION,
                    f"Tabelle {orph.table_number}: continuation rows without "
                    f"caption at top of page {page_no} (recovered)",
                    table_id=orph_spec.table_id if orph_spec else None,
                    page=page_no))
        for f in frags:
            by_number.setdefault(f.table_number, []).append((page_no, f))
        if frags:
            last = max(frags, key=lambda f: f.sub_tables[0].top_y)
            if any(st.bottom_y is None for st in last.sub_tables):
                spec = SPEC_BY_NUMBER.get(last.table_number)
                ax = _open_anchor_x(last, spec)
                open_table = (last.table_number, ax) if ax is not None else None
            else:
                open_table = None
    out: list[ParsedTable] = []
    for spec in TABLE_SPECS:
        if spec.number is None:
            continue
        frags = by_number.get(spec.number, [])
        t = _parse_numbered(spec, frags)
        t.warnings.extend(w for w in orphan_notes
                          if w.table_id == spec.table_id)
        out.append(t)
    return out
