"""Header verification (D5): compare detected header words with the expected
German headers.  Mismatches produce structured warnings, never exceptions.

The matcher walks the detected header words in PDF stream order and looks for
each expected header as a consecutive token run.  It also records, for every
matched expected header, the x0 of its first word (the column's visual left
edge) so the column mapper can pair detected columns with expected headers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .geometry import Word
from .models import ParseWarning

W_HEADER_MISSING = "HEADER_MISSING_COLUMN"
W_HEADER_EXTRA = "HEADER_UNEXPECTED_COLUMN"


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class HeaderMatch:
    """Result of matching expected headers against detected header words."""

    # for each expected header (by index): (word_start_idx, word_end_idx_excl) or None
    spans: list[tuple[int, int] | None] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    # header words not consumed by any expected header (by stream index)
    extra_word_idx: list[int] = field(default_factory=list)


def check_headers(header_words: list[Word], expected_headers: list[str],
                  page: int, table_id: str, is_continuation: bool = False) -> HeaderMatch:
    """Sequential token-run matcher.

    ``header_words`` is in PDF stream order (the logical cell order, which also
    works for staggered multi-line headers where the visual order differs).
    """
    words = [normalize(w.text) for w in header_words]
    res = HeaderMatch()

    # token runs for expected headers; single words may also match a header whose
    # first token is a single word, so keep exact runs only
    pos = 0
    spans: list[tuple[int, int] | None] = []
    consumed: set[int] = set()
    for exp in expected_headers:
        tokens = exp.split(" ")
        found: int | None = None
        if len(tokens) == 1:
            for p in range(pos, len(words)):
                if words[p] == tokens[0]:
                    found = p
                    break
        else:
            for p in range(pos, len(words) - len(tokens) + 1):
                if words[p:p + len(tokens)] == tokens:
                    found = p
                    break
        if found is None:
            spans.append(None)
            res.warnings.append(ParseWarning(
                W_HEADER_MISSING,
                f"expected header column {exp!r} not found",
                table_id=table_id, page=page,
                expected=exp + (" [continuation]" if is_continuation else "")))
        else:
            spans.append((found, found + len(tokens)))
            consumed.update(range(found, found + len(tokens)))
            if found > pos:
                extra = " ".join(words[pos:found])
                if extra:
                    res.warnings.append(ParseWarning(
                        W_HEADER_EXTRA,
                        f"unexpected header text before column {exp!r}: {extra!r}",
                        table_id=table_id, page=page, found=extra))
            pos = found + len(tokens)
    if pos < len(words):
        extra = " ".join(words[pos:])
        if extra:
            res.warnings.append(ParseWarning(
                W_HEADER_EXTRA,
                f"unexpected trailing header text: {extra!r}",
                table_id=table_id, page=page, found=extra))
    res.spans = spans
    for i, w in enumerate(header_words):
        if i not in consumed:
            res.extra_word_idx.append(i)
    return res


def header_left_edges(match: HeaderMatch, header_words: list[Word]) -> list[float | None]:
    """x0 of the first word of each expected header (visual column left edge)."""
    out: list[float | None] = []
    for span in match.spans:
        if span is None:
            out.append(None)
        else:
            out.append(min(header_words[i].x0 for i in range(span[0], span[1])))
    return out
