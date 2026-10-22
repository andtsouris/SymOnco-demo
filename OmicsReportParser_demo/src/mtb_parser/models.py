"""Core data model for the MTB report parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Word:
    """A single word extracted from the PDF (stream order preserved)."""

    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    bold: bool = False
    stream_idx: int = 0

    @property
    def x_center(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def y_center(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class TextLine:
    """Visual line: words sharing (approximately) the same top coordinate."""

    words: list[Word] = field(default_factory=list)  # sorted by x0

    @property
    def y0(self) -> float:
        return min(w.y0 for w in self.words)

    @property
    def y1(self) -> float:
        return max(w.y1 for w in self.words)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass(frozen=True)
class RuleSegment:
    """A horizontal line segment (booktabs rule part)."""

    y: float
    x0: float
    x1: float

    @property
    def x_center(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class RuleBand:
    """Horizontal rule segments sharing the same y coordinate."""

    y: float
    segments: list[RuleSegment] = field(default_factory=list)  # sorted by x0


@dataclass
class SubTable:
    """One mini-table on a page: bounded by rule lines, may be one of several
    side-by-side sub-tables (t07/t08) or stacked sub-tables (t01)."""

    page_no: int  # 1-based
    x0: float
    x1: float
    top_y: float
    mid_y: float
    bottom_y: Optional[float]  # None -> table continues on the next page
    table_number: int
    is_continuation: bool
    caption_text: str
    header_words: list[Word] = field(default_factory=list)  # stream order
    body_words: list[Word] = field(default_factory=list)  # stream order


@dataclass
class TableFragment:
    """All sub-tables of one table caption on one page."""

    page_no: int
    table_number: int
    is_continuation: bool
    caption_text: str
    sub_tables: list[SubTable] = field(default_factory=list)


@dataclass
class ParseWarning:
    """Structured, non-fatal parse warning (see DEVELOPMENT_PLAN.md §3)."""

    code: str
    message: str
    table_id: Optional[str] = None
    page: Optional[int] = None
    column: Optional[int] = None
    expected: Optional[str] = None
    found: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "code": self.code,
            "message": self.message,
            "table_id": self.table_id,
            "page": self.page,
        }
        if self.column is not None:
            d["column"] = self.column
        if self.expected is not None:
            d["expected"] = self.expected
        if self.found is not None:
            d["found"] = self.found
        return d


@dataclass
class ParsedTable:
    """A fully assembled table (all fragments stitched)."""

    table_id: str
    slug: str
    table_number: Optional[int]
    title: str
    columns: list[str]
    rows: list[dict] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    # raw expected headers for provenance
    expected_headers: list[str] = field(default_factory=list)
