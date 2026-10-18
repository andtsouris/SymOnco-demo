import ast
import re
from collections.abc import Iterable

from mipro_v2.tasks import TaskSpec, get_task


def parse_entity_list(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return [item.strip() for item in text.split(";") if item.strip()]
        value = parsed
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Iterable) and not isinstance(value, (bytes, dict)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    return [str(value).strip()]


def normalize_entity(value: str, task: str | TaskSpec) -> str:
    spec = get_task(task) if isinstance(task, str) else task
    text = str(value).strip().strip(".,")

    if spec.key == "publications":
        text = re.sub(
            r"^.*?(?:doi\.org/|doi/abs/|doi/)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"_suppl\S*", "", text, flags=re.IGNORECASE)
        return text.strip().strip(".,").casefold()

    if spec.key == "clinical_trials":
        text = re.sub(r"^NCT-Nr:\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^NCT\s*", "", text, flags=re.IGNORECASE)
        return text.strip().strip(".,").casefold()

    if spec.key == "genes":
        return text.upper()

    if spec.key == "evidence_levels":
        text = text.casefold()
        while text.startswith(("el", "m")):
            text = text[2:] if text.startswith("el") else text[1:]
        return text.strip()

    return text.casefold()


def jaccard_score(gold: object, predicted: object, task: str | TaskSpec) -> float:
    spec = get_task(task) if isinstance(task, str) else task
    gold_set = {
        normalize_entity(value, spec)
        for value in parse_entity_list(gold)
        if value.strip()
    }
    predicted_set = {
        normalize_entity(value, spec)
        for value in parse_entity_list(predicted)
        if value.strip()
        and not (
            spec.key == "publications"
            and value.strip().upper().startswith("NCT")
        )
    }
    union = gold_set | predicted_set
    return len(gold_set & predicted_set) / len(union) if union else 1.0
