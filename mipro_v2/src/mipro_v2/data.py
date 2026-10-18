import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mipro_v2.tasks import TaskSpec, get_task


@dataclass(frozen=True)
class RecommendationRecord:
    rec_id: str
    text: str
    labels: list[dict[str, Any]]
    annotation_count: int


def _raw_record(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"Record {index} must be a JSON object")
    record = item.get("record", item)
    if not isinstance(record, dict):
        raise ValueError(f"Record {index} has no valid Label Studio task record")
    return record


def load_recommendations(path: str | Path) -> list[RecommendationRecord]:
    """Load either raw Label Studio tasks or legacy Recommendation exports."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Recommendation export must be a JSON array")

    recommendations = []
    for index, item in enumerate(data):
        record = _raw_record(item, index)
        rec_id = record.get("id")
        record_data = record.get("data") or {}
        if not isinstance(record_data, dict):
            raise ValueError(f"Record {index} data must be an object")
        text = record_data.get("text")
        annotations = record.get("annotations") or []
        if rec_id is None or not isinstance(text, str) or not text.strip():
            raise ValueError(f"Record {index} must include an id and non-empty data.text")
        if not isinstance(annotations, list):
            raise ValueError(f"Record {index} annotations must be a list")

        labels = []
        if len(annotations) == 1:
            if not isinstance(annotations[0], dict):
                raise ValueError(f"Record {index} annotation must be an object")
            result = annotations[0].get("result") or []
            if not isinstance(result, list):
                raise ValueError(f"Record {index} annotation result must be a list")
            if any(not isinstance(entry, dict) for entry in result):
                raise ValueError(f"Record {index} contains a non-object annotation")
            labels = [entry for entry in result if entry.get("type") == "labels"]
        recommendations.append(
            RecommendationRecord(
                rec_id=str(rec_id),
                text=text,
                labels=labels,
                annotation_count=len(annotations),
            )
        )
    return recommendations


def task_examples(
    recommendations: list[RecommendationRecord],
    task: str | TaskSpec,
) -> tuple[list[dict[str, Any]], int]:
    """Return text/gold examples and a count skipped for ambiguous annotations."""
    spec = get_task(task) if isinstance(task, str) else task
    examples = []
    skipped = 0
    for recommendation in recommendations:
        if recommendation.annotation_count != 1:
            skipped += 1
            continue

        values = []
        for label in recommendation.labels:
            nested = label.get("value") or {}
            if not isinstance(nested, dict):
                raise ValueError(
                    f"Recommendation {recommendation.rec_id} has invalid label value"
                )
            label_names = label.get("labels") or nested.get("labels") or []
            if not set(spec.label_names).intersection(label_names):
                continue
            value = label.get("text") or nested.get("text")
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
        examples.append({"text": recommendation.text, spec.output_field: values})
    return examples, skipped
