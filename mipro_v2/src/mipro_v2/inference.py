import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mipro_v2.data import load_recommendations
from mipro_v2.metrics import parse_entity_list
from mipro_v2.optimizer import _build_signature
from mipro_v2.service_client import enrich_extractions
from mipro_v2.tasks import TASKS, get_task


def extract_records(
    recommendations: list[Any],
    models: dict[str, Any],
) -> list[dict[str, Any]]:
    results = []
    for recommendation in recommendations:
        extractions = {}
        for task, program in models.items():
            spec = get_task(task)
            prediction = program(text=recommendation.text)
            extractions[spec.output_field] = parse_entity_list(
                getattr(prediction, spec.output_field)
            )
        results.append(
            {
                "rec_id": recommendation.rec_id,
                "extractions": extractions,
            }
        )
    return results


def _load_program(dspy: Any, task: str, model_path: str) -> Any:
    spec = get_task(task)
    program = dspy.Predict(signature=_build_signature(dspy, spec))
    program.load(model_path)
    return program


async def run_pipeline(
    data_path: str,
    model_paths: dict[str, str],
    output_path: str,
    *,
    enrich: bool = False,
    publications_url: str = "http://127.0.0.1:5170",
    trials_url: str = "http://127.0.0.1:5172",
    drugs_url: str = "http://127.0.0.1:5171",
) -> dict[str, Any]:
    if not model_paths:
        raise ValueError("Provide at least one --model TASK=PATH")
    unknown_tasks = set(model_paths) - TASKS.keys()
    if unknown_tasks:
        raise ValueError(f"Unknown model task(s): {', '.join(sorted(unknown_tasks))}")

    load_dotenv()
    model_name = os.getenv("MIPRO_MODEL")
    if not model_name:
        raise ValueError("Set MIPRO_MODEL before running saved extractors")
    recommendations = load_recommendations(data_path)
    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("DSPy is required to load optimized models") from exc

    language_model = dspy.LM(
        model=model_name,
        api_base=os.getenv("MIPRO_API_BASE"),
        api_key=os.getenv("MIPRO_API_KEY"),
    )
    dspy.settings.configure(lm=language_model, adapter=dspy.ChatAdapter())
    models = {
        task: _load_program(dspy, task, path)
        for task, path in model_paths.items()
    }
    results = extract_records(recommendations, models)
    if enrich:
        results = await enrich_extractions(
            results,
            publications_url=publications_url,
            trials_url=trials_url,
            drugs_url=drugs_url,
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "recommendations": len(results),
        "enriched": enrich,
        "output_path": str(output),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run saved MIPROv2 extractors and optionally call fetch services."
    )
    parser.add_argument("--data", required=True, help="Label Studio export JSON")
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        metavar="TASK=PATH",
        help="Optimized model; may be supplied once per extraction task",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--enrich", action="store_true")
    parser.add_argument(
        "--publications-url",
        default=os.getenv("FETCH_PUBLICATIONS_URL", "http://127.0.0.1:5170"),
    )
    parser.add_argument(
        "--trials-url",
        default=os.getenv("FETCH_TRIALS_URL", "http://127.0.0.1:5172"),
    )
    parser.add_argument(
        "--drugs-url",
        default=os.getenv("FETCH_DRUGS_URL", "http://127.0.0.1:5171"),
    )
    return parser


def _parse_model_paths(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        task, separator, path = value.partition("=")
        if not separator or not path:
            raise ValueError(f"Invalid --model {value!r}; expected TASK=PATH")
        if task in result:
            raise ValueError(f"Model task {task!r} was supplied more than once")
        result[task] = path
    return result


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    result = asyncio.run(
        run_pipeline(
            data_path=args.data,
            model_paths=_parse_model_paths(args.model),
            output_path=args.output,
            enrich=args.enrich,
            publications_url=args.publications_url,
            trials_url=args.trials_url,
            drugs_url=args.drugs_url,
        )
    )
    print(json.dumps(result, indent=2))
