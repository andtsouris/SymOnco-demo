"""Self-validation of parsed reports (D4/D5 invariants).

Checks (non-fatal; results are returned as a list of issue strings):
* every registered table id is present,
* per table: all rows have exactly the same key set (fixed schema, D4),
* row key sets contain the declared columns,
* optional golden-cell expectations (dev/test).
"""

from __future__ import annotations

from .registry import TABLE_SPECS


def check_report(tables: list[dict], golden: dict | None = None) -> list[str]:
    """tables: list of table dicts as written to JSON (see writers.table_to_dict).

    golden: optional {(table_id, row_index, column): expected_value}.
    """
    issues: list[str] = []
    by_id = {t["table_id"]: t for t in tables}
    expected_ids = {s.table_id for s in TABLE_SPECS}
    for tid in sorted(expected_ids - set(by_id)):
        issues.append(f"table {tid} missing from output")

    for t in tables:
        tid = t["table_id"]
        cols = t["columns"]
        key_sets: set[frozenset] = set()
        for i, row in enumerate(t["rows"]):
            ks = frozenset(row.keys())
            key_sets.add(ks)
            if set(cols) - ks:
                issues.append(f"{tid}: row {i} missing columns "
                              f"{sorted(set(cols) - ks)}")
                break
        if len(key_sets) > 1:
            issues.append(f"{tid}: inconsistent row key sets across "
                          f"{len(key_sets)} variants (schema drift)")
        if golden:
            for (g_tid, ri, col), expected_val in golden.items():
                if g_tid != tid:
                    continue
                if ri >= len(t["rows"]):
                    issues.append(f"{tid}: golden row {ri} out of range")
                    continue
                actual = t["rows"][ri].get(col)
                if actual != expected_val:
                    issues.append(f"{tid}: golden cell [{ri}][{col}] "
                                  f"expected {expected_val!r}, got {actual!r}")
    return issues
