"""JSON writers (D1: JSON only).

Layout:
    parsed_reports/index.json
    parsed_reports/<sample_id>/report.json
    parsed_reports/<sample_id>/tables/<slug>.json
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .models import ParsedTable

PARSER_VERSION = "0.1.0"


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def table_to_dict(t: ParsedTable) -> dict:
    return {
        "table_id": t.table_id,
        "table_number": t.table_number,
        "slug": t.slug,
        "title": t.title,
        "source_pages": t.pages,
        "columns": t.columns,
        "expected_headers": t.expected_headers,
        "row_count": len(t.rows),
        "warnings": [w.to_dict() for w in t.warnings],
        "rows": t.rows,
    }


def _sample_id_from_filename(path: Path) -> str:
    m = __import__("re").match(r"Report_([A-Za-z0-9\-]+)\.pdf$", path.name)
    return m.group(1) if m else path.stem


def write_report(sample_id: str, source_file: str, metadata: dict,
                 reference_genomes: list[str], tables: list[ParsedTable],
                 out_root: Path) -> dict:
    d = out_root / sample_id
    (d / "tables").mkdir(parents=True, exist_ok=True)

    all_warnings = []
    for t in tables:
        for w in t.warnings:
            all_warnings.append(w.to_dict())

    report = {
        "sample_id": sample_id,
        "source_file": source_file,
        "generated_at": _now(),
        "parser_version": PARSER_VERSION,
        "metadata": {**metadata, "reference_genomes": reference_genomes},
        "n_tables": len(tables),
        "n_warnings": len(all_warnings),
        "warnings": all_warnings,
        "tables": [
            {
                "table_id": t.table_id,
                "table_number": t.table_number,
                "slug": t.slug,
                "title": t.title,
                "source_pages": t.pages,
                "row_count": len(t.rows),
                "file": f"tables/{t.slug}.json",
                "n_warnings": len(t.warnings),
            }
            for t in tables
        ],
    }
    _write_json(d / "report.json", report)
    for t in tables:
        _write_json(d / "tables" / f"{t.slug}.json", table_to_dict(t))
    return report


def write_index(out_root: Path, entries: list[dict]) -> None:
    index = {
        "generated_at": _now(),
        "parser_version": PARSER_VERSION,
        "reports": entries,
    }
    _write_json(out_root / "index.json", index)


def _write_json(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
