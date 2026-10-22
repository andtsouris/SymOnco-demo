"""Appendix C (Abkürzungsverzeichnis) and D (Programmversionen).

Unlike the numbered tables these have no booktabs rules:
* Appendix C: two columns (abbreviation at x~72, meaning at x~171), no header row.
* Appendix D: bullet lists under 'D.1 Referenzgenom' / 'D.2 Programmversionen'.

Column names are derived (no printed header row) and therefore fixed by the
registry: Abkürzung/Bedeutung and Software/Version (D3/D4).
"""

from __future__ import annotations

import re

from .geometry import FOOTER_Y, group_lines
from .models import ParsedTable, ParseWarning
from .registry import SPEC_BY_ID

W_APP_NOT_FOUND = "APPENDIX_NOT_FOUND"
W_APP_ROW = "APPENDIX_PARSE_ISSUE"

APP_C_SPLIT_X = 160.0     # words left of this: abbreviation, right: meaning
_VERSION_RE = re.compile(r"^[vV]?\d")


def _page_words(page_data: list[tuple], pno: int) -> list:
    return page_data[pno - 1][1]


def _parse_appendix_c(page_data: list[tuple]) -> ParsedTable:
    spec = SPEC_BY_ID["app_c"]
    rows: list[dict] = []
    pages: list[int] = []
    warns: list[ParseWarning] = []

    title_page = None
    title_y = 0.0
    # search from the last page backwards: the real appendix is at the end of the
    # document, while the table of contents (early pages) also mentions the title.
    for pno, words, _b, _f in reversed(page_data):
        for ln in group_lines(words):
            if (len(ln.words) >= 2 and ln.words[0].text == "C"
                    and ln.words[0].x0 < 80
                    and ln.words[1].text.startswith("Abkürzungsverzeichnis")):
                title_page, title_y = pno, ln.y0
                break
        if title_page:
            break
    if title_page is None:
        return ParsedTable(
            table_id=spec.table_id, slug=spec.slug, table_number=None,
            title=spec.title_fallback, columns=list(spec.expected_headers),
            rows=[], pages=[],
            warnings=[ParseWarning(W_APP_NOT_FOUND, "Appendix C title not found",
                                   table_id=spec.table_id)],
            expected_headers=list(spec.expected_headers))

    pages.append(title_page)
    for pno in range(title_page, len(page_data) + 1):
        for ln in group_lines(_page_words(page_data, pno)):
            if pno == title_page and ln.y0 <= title_y:
                continue
            if ln.words[0].y0 >= FOOTER_Y - 5:
                break
            first = ln.words[0]
            t = ln.text
            # stop at the next section heading: single letter at x<80 followed by
            # a title word in the heading column (x<160).  Single-letter
            # *abbreviations* ('D', 'N') have their meaning at x>=160 and are kept.
            if (first.x0 < 80 and len(first.text) == 1 and first.text.isupper()
                    and len(ln.words) >= 2 and ln.words[1].x0 < APP_C_SPLIT_X
                    and pno != title_page):
                return _finish(spec, rows, pages, warns)
            if t.startswith("Tabelle "):
                return _finish(spec, rows, pages, warns)
            abbr_words = [w for w in ln.words if w.x0 < APP_C_SPLIT_X]
            mean_words = [w for w in ln.words if w.x0 >= APP_C_SPLIT_X]
            if abbr_words:
                if pno not in pages:
                    pages.append(pno)
                rows.append({"Abkürzung": " ".join(w.text for w in abbr_words),
                             "Bedeutung": " ".join(w.text for w in mean_words) or None})
            elif mean_words and rows:
                if pno not in pages:
                    pages.append(pno)
                prev = rows[-1]["Bedeutung"]
                rows[-1]["Bedeutung"] = (prev + " " if prev else "") + " ".join(
                    w.text for w in mean_words)
            elif not rows:
                warns.append(ParseWarning(W_APP_ROW, f"unparsed appendix C line: {t!r}",
                                          table_id=spec.table_id, page=pno))
    return _finish(spec, rows, pages, warns)


def _parse_appendix_d(page_data: list[tuple]) -> tuple[ParsedTable, list[str]]:
    """Returns (table, reference_genomes)."""
    spec = SPEC_BY_ID["app_d"]
    rows: list[dict] = []
    pages: list[int] = []
    warns: list[ParseWarning] = []
    genomes: list[str] = []

    in_d2 = False
    in_d1 = False
    # find the last page containing 'D.2' first (TOC on early pages also matches)
    d2_page = None
    for pno, words, _b, _f in reversed(page_data):
        if any(ln.words and ln.words[0].text == "D.2" for ln in group_lines(words)):
            d2_page = pno
            break
    for pno in range(d2_page or 1, len(page_data) + 1):
        lines = group_lines(_page_words(page_data, pno))
        pages.append(pno)
        for ln in lines:
            t = ln.text
            if ln.words[0].text == "D.2":
                in_d2, in_d1 = True, False
                continue
            if ln.words[0].text == "D.1":
                in_d1, in_d2 = True, False
                continue
            if ln.words[0].text.startswith("•"):
                ws = [w for w in ln.words if not w.text.startswith("•")]
                if not ws:
                    continue
                if in_d1:
                    genomes.append(" ".join(w.text for w in ws))
                    continue
                if in_d2:
                    if len(ws) > 1 and _VERSION_RE.match(ws[-1].text):
                        name = " ".join(w.text for w in ws[:-1])
                        ver = ws[-1].text
                    else:
                        name = " ".join(w.text for w in ws)
                        ver = None
                    rows.append({"Software": name, "Version": ver})
            elif in_d2 and not t.startswith("D."):
                # first non-bullet line after the bullet list (footer) -> stop
                break
    if not rows:
        warns.append(ParseWarning(W_APP_NOT_FOUND, "Appendix D (Programmversionen) not found",
                                  table_id=spec.table_id))
    table = _finish(spec, rows, pages, warns)
    table.title = "Programmversionen"
    return table, genomes


def _finish(spec, rows, pages, warns) -> ParsedTable:
    return ParsedTable(
        table_id=spec.table_id, slug=spec.slug, table_number=None,
        title=spec.title_fallback, columns=list(spec.expected_headers),
        rows=rows, pages=pages, warnings=warns,
        expected_headers=list(spec.expected_headers))


def parse_appendices(page_data: list[tuple]) -> tuple[list[ParsedTable], list[str]]:
    t_c = _parse_appendix_c(page_data)
    t_d, genomes = _parse_appendix_d(page_data)
    return [t_c, t_d], genomes
