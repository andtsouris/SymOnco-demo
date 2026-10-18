import os
import random
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mipro_v2.data import load_recommendations, task_examples
from mipro_v2.metrics import jaccard_score, parse_entity_list
from mipro_v2.report import write_error_report
from mipro_v2.tasks import TaskSpec, get_task


def _build_signature(dspy: Any, spec: TaskSpec) -> type:
    name = "".join(part.title() for part in spec.key.split("_")) + "Finder"
    fields = {
        "__annotations__": {
            "text": str,
            spec.output_field: list[str],
        },
        "__doc__": spec.description,
        "text": dspy.InputField(),
        spec.output_field: dspy.OutputField(desc=spec.description),
    }
    return type(name, (dspy.Signature,), fields)


def _split_examples(
    examples: list[dict[str, Any]],
    output_field: str,
    test_size: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if len(examples) < 2:
        raise ValueError("At least two labeled recommendations are required")
    indices = list(range(len(examples)))
    random.Random(seed).shuffle(indices)
    test_count = max(1, round(len(indices) * test_size))
    test_count = min(test_count, len(indices) - 1)
    test_indices = set(indices[:test_count])
    train = [item for index, item in enumerate(examples) if index not in test_indices]
    test = [item for index, item in enumerate(examples) if index in test_indices]
    return train, test


def optimize(
    task: str,
    data_path: str | Path,
    output_path: str | Path,
    *,
    model_name: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    num_candidates: int = 20,
    num_trials: int = 20,
    num_threads: int = 1,
    test_size: float = 0.2,
    seed: int = 42,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Tune one extraction task, save the DSPy program, and write reports."""
    load_dotenv()
    spec = get_task(task)
    model_name = model_name or os.getenv("MIPRO_MODEL")
    api_base = api_base or os.getenv("MIPRO_API_BASE")
    api_key = api_key or os.getenv("MIPRO_API_KEY")
    if not model_name:
        raise ValueError("Set MIPRO_MODEL or pass --model")

    recommendations = load_recommendations(data_path)
    examples, skipped = task_examples(recommendations, spec)
    train_examples, test_examples = _split_examples(
        examples, spec.output_field, test_size, seed
    )

    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError(
            "DSPy is required to run optimization; install this package with "
            "`pip install -e .`"
        ) from exc

    language_model = dspy.LM(
        model=model_name,
        api_base=api_base,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    dspy.settings.configure(lm=language_model, adapter=dspy.ChatAdapter())
    signature = _build_signature(dspy, spec)
    trainset = [
        dspy.Example(**item).with_inputs("text") for item in train_examples
    ]
    devset = [
        dspy.Example(**item).with_inputs("text") for item in test_examples
    ]

    def metric(example: Any, prediction: Any, trace: Any = None) -> float:
        return jaccard_score(
            getattr(example, spec.output_field),
            getattr(prediction, spec.output_field),
            spec,
        )

    optimizer = dspy.MIPROv2(
        metric=metric,
        verbose=False,
        auto=None,
        num_candidates=num_candidates,
        num_threads=num_threads,
    )
    program = optimizer.compile(
        dspy.Predict(signature=signature),
        trainset=trainset,
        num_trials=num_trials,
    )
    evaluation = dspy.Evaluate(
        devset=devset,
        metric=metric,
        num_threads=num_threads,
        display_progress=False,
    )(program)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    program.save(str(output))
    predictions = []
    for example in test_examples:
        prediction = program(text=example["text"])
        predictions.append(
            parse_entity_list(getattr(prediction, spec.output_field))
        )
    json_report, html_report = write_error_report(
        spec,
        test_examples,
        predictions,
        output,
    )
    return {
        "score": evaluation.score,
        "train_examples": len(train_examples),
        "test_examples": len(test_examples),
        "skipped_ambiguous_records": skipped,
        "model_path": str(output),
        "json_report": str(json_report),
        "html_report": str(html_report),
    }
