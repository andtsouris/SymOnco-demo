# MTB WGS/WES Report Parser

This is a demo version of our internal tool that parses the standardized whole-genome and whole-exome sequencing reports from the Molecular Tumor Board of Uniklinik Freiburg.

## Quick start

```bash
cd OmicsReportParser
/usr/local/bin/uv venv .venv                      # once
/usr/local/bin/uv pip install --python .venv/bin/python pymupdf
PYTHONPATH=src .venv/bin/python -m mtb_parser     # parse raw_reports/ -> parsed_reports/
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

Options:

```
python -m mtb_parser [PDF ...] [--input DIR] [--out DIR] [--quiet]
```

## Output layout

```
parsed_reports/
├── index.json                          # all samples, table list + row counts
├── <sample_name>/
│   ├── report.json                     # General information: metadata, warnings, table index
│   └── tables/
│       ├── 01_key_results.json
│       ├── 02_acmg_classified_mutations.json
│       ├── ...
│       ├── appendix_c_abbreviations.json
│       └── appendix_d_software.json
└── <sample_name>/
    └── ...
```


## Warning codes

The extracted tables are compared to the expected format and all discrepencies are marked using specific flags.

`TABLE_NOT_FOUND`, `TABLE_EMPTY`, `HEADER_MISSING_COLUMN`,
`HEADER_UNEXPECTED_COLUMN`, `CONTINUATION_HEADER_DRIFT`, `COLUMN_COUNT_DRIFT`,
`COLUMN_MISSING`, `SUBTABLE_UNEXPECTED`, `ROW_ANOMALY`,
`CONTINUATION_WITHOUT_CAPTION`, `APPENDIX_NOT_FOUND`, `APPENDIX_PARSE_ISSUE`.


## Architecture

```
src/mtb_parser/
├── geometry.py     # words (stream order, bold), rule bands, table fragments,
│                   #   stacked/side-by-side sub-tables, orphan-continuation rows
├── columns.py      # column edges (registry-seeded from matched header cells;
│                   #   heuristic fallback) + word assignment
├── rows.py         # anchor-based logical rows, wrap-aware cell joining, hotspot
├── registry.py     # TABLE_SPECS: per-table expected German headers (= column
│                   #   names), anchors, blocks, forward-fill, hotspot flag
├── header_check.py # sequential header matcher vs registry -> warnings (D5)
├── tables.py       # fragment stitching, fixed-schema projection (D4)
├── metadata.py     # cover-page sample id / report date
├── appendices.py   # appendix C (2-column glossary) and D (software bullets)
├── writers.py      # JSON writers (D1)
├── validate.py     # structural self-checks
└── cli.py          # python -m mtb_parser
```

Why custom geometry instead of a PDF table library: these reports use booktabs
tables (horizontal rules only, no row/vertical rules), staggered multi-line headers,
multi-page continuations, stacked and side-by-side sub-tables — tested
`pymupdf.find_tables()` and `pdfplumber`; both drop characters (e.g. `p.G12D` →
`pG12D`) or fail to segment these tables at all. See `PLAN.md`.
