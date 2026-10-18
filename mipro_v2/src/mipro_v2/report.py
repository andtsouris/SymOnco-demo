import html
import json
from pathlib import Path
from typing import Any

from mipro_v2.metrics import jaccard_score, parse_entity_list
from mipro_v2.tasks import TaskSpec, get_task


def write_error_report(
    task: str | TaskSpec,
    examples: list[dict[str, Any]],
    predictions: list[list[str]],
    output_path: str | Path,
) -> tuple[Path, Path]:
    spec = get_task(task) if isinstance(task, str) else task
    if len(examples) != len(predictions):
        raise ValueError("Each example must have exactly one prediction")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, (example, predicted) in enumerate(zip(examples, predictions), start=1):
        gold = parse_entity_list(example[spec.output_field])
        score = jaccard_score(gold, predicted, spec)
        rows.append(
            {
                "index": index,
                "text": example["text"],
                "gold": gold,
                "predicted": predicted,
                "jaccard": score,
            }
        )

    json_path = output.with_suffix(".report.json")
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    sections = []
    for row in rows:
        sections.append(
            "<section><h2>Example "
            f"{row['index']}</h2><p>Jaccard: {row['jaccard']:.3f}</p>"
            f"<pre>{html.escape(row['text'])}</pre>"
            f"<p><b>Gold:</b> {html.escape(str(row['gold']))}</p>"
            f"<p><b>Predicted:</b> {html.escape(str(row['predicted']))}</p>"
            "</section>"
        )
    html_path = output.with_suffix(".report.html")
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>"
        f"{html.escape(spec.key)} extraction report</title></head><body>"
        f"<h1>{html.escape(spec.key)} extraction report</h1>"
        + "".join(sections)
        + "</body></html>",
        encoding="utf-8",
    )
    return json_path, html_path
