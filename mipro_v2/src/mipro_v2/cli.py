import argparse
import json

from mipro_v2.optimizer import optimize
from mipro_v2.tasks import TASKS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tune a recommendation-letter extractor with DSPy MIPROv2."
    )
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--data", required=True, help="Label Studio export JSON")
    parser.add_argument("--output", required=True, help="Path for saved DSPy model")
    parser.add_argument("--model", help="DSPy LM model identifier")
    parser.add_argument("--api-base", help="OpenAI-compatible API base URL")
    parser.add_argument("--num-candidates", type=int, default=20)
    parser.add_argument("--num-trials", type=int, default=20)
    parser.add_argument("--num-threads", type=int, default=1)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=2048)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = optimize(
        task=args.task,
        data_path=args.data,
        output_path=args.output,
        model_name=args.model,
        api_base=args.api_base,
        num_candidates=args.num_candidates,
        num_trials=args.num_trials,
        num_threads=args.num_threads,
        test_size=args.test_size,
        seed=args.seed,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    print(json.dumps(result, indent=2))
