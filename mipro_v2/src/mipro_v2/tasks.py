from dataclasses import dataclass


@dataclass(frozen=True)
class TaskSpec:
    key: str
    output_field: str
    label_names: tuple[str, ...]
    description: str


TASKS = {
    "publications": TaskSpec(
        key="publications",
        output_field="pubs",
        label_names=("Publication",),
        description=(
            "Extract publication identifiers and citation strings from the "
            "recommendation letter. Return only a Python list of strings."
        ),
    ),
    "clinical_trials": TaskSpec(
        key="clinical_trials",
        output_field="ctrial",
        label_names=("Clinical Trial",),
        description=(
            "Extract clinical-trial identifiers and study names from the "
            "recommendation letter. Keep NCT identifiers in NCT######## form "
            "when present. Return only a Python list of strings."
        ),
    ),
    "genes": TaskSpec(
        key="genes",
        output_field="genes",
        label_names=("Gene",),
        description=(
            "Extract gene names and gene variant notation as written in the "
            "recommendation letter. Do not include trials or publications. "
            "Return only a Python list of strings."
        ),
    ),
    "drugs": TaskSpec(
        key="drugs",
        output_field="drugs",
        label_names=("Drug",),
        description=(
            "Extract drug names and drug aliases mentioned in the "
            "recommendation letter. Return only a Python list of strings."
        ),
    ),
    "evidence_levels": TaskSpec(
        key="evidence_levels",
        output_field="evLevs",
        label_names=("Evidence Level",),
        description=(
            "Extract evidence-level labels from the recommendation letter. "
            "Return only a Python list of strings."
        ),
    ),
}


def get_task(task_name: str) -> TaskSpec:
    try:
        return TASKS[task_name]
    except KeyError as exc:
        valid = ", ".join(TASKS)
        raise ValueError(f"Unknown task {task_name!r}; choose one of: {valid}") from exc
