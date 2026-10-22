"""Command line interface.

Usage:
    python -m mtb_parser [PDF ...] [--input DIR] [--out DIR] [--quiet]

Defaults: all *.pdf in ./raw_reports, output to ./parsed_reports.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymupdf

from . import appendices, metadata as meta_mod, tables as tables_mod, writers
from .geometry import parse_page


def parse_pdf(path: Path) -> dict:
    """Parse one report PDF -> report dict (without writing files)."""
    doc = pymupdf.open(str(path))
    sample_id = writers._sample_id_from_filename(path)

    page_data = []
    for i in range(len(doc)):
        words, bands, frags = parse_page(i + 1, doc[i])
        page_data.append((i + 1, words, bands, frags))

    numbered = tables_mod.parse_tables(page_data)
    appendix_tables, genomes = appendices.parse_appendices(page_data)
    all_tables = numbered + appendix_tables

    md = meta_mod.extract_metadata(page_data[0][1]) if page_data else {}
    md["sample_id"] = sample_id

    return {
        "sample_id": sample_id,
        "source_file": str(path),
        "metadata": {**md, "reference_genomes": genomes},
        "tables": all_tables,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mtb_parser",
                                 description="Parse MTB MTB-AI omics PDF reports "
                                             "into per-table JSON files.")
    ap.add_argument("pdfs", nargs="*", type=Path,
                    help="report PDFs (default: all *.pdf in --input)")
    ap.add_argument("--input", type=Path, default=Path("raw_reports"),
                    help="directory containing report PDFs")
    ap.add_argument("--out", type=Path, default=Path("parsed_reports"),
                    help="output root directory")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    pdfs = list(args.pdfs) if args.pdfs else sorted(args.input.glob("*.pdf"))
    if not pdfs:
        print(f"error: no PDFs found (looked in {args.input})", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    entries = []
    rc = 0
    for path in pdfs:
        if not path.is_file():
            print(f"error: {path} not found", file=sys.stderr)
            rc = 2
            continue
        if not args.quiet:
            print(f"parsing {path} ...")
        data = parse_pdf(path)
        report = writers.write_report(
            data["sample_id"], path.name, data["metadata"],
            data["metadata"]["reference_genomes"], data["tables"], args.out)
        n_rows = sum(t["row_count"] for t in report["tables"])
        print(f"  {data['sample_id']}: {report['n_tables']} tables, "
              f"{n_rows} rows, {report['n_warnings']} warnings")
        for w in report["warnings"]:
            if not args.quiet:
                where = f" (page {w['page']})" if w.get("page") else ""
                print(f"    WARNING [{w['code']}] {w['message']}{where}")
        entries.append({
            "sample_id": data["sample_id"],
            "source_file": path.name,
            "report_file": f"{data['sample_id']}/report.json",
            "n_tables": report["n_tables"],
            "total_rows": n_rows,
            "n_warnings": report["n_warnings"],
            "tables": {t["table_id"]: {"file": t["file"],
                                       "rows": t["row_count"]}
                       for t in report["tables"]},
        })
    writers.write_index(args.out, entries)
    if not args.quiet:
        print(f"wrote {args.out}/index.json")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
