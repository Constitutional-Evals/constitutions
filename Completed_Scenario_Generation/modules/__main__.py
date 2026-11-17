"""Command-line entry point: python -m modules."""

import argparse
from pathlib import Path

from . import config as cfg
from .client import OpenRouterClient, obtain_openrouter_key
from .core import initialize_workspace
from .pipeline import run_pipeline
from .stages import show_coverage


def main():
    parser = argparse.ArgumentParser(description="Generate and evaluate scenarios")
    parser.add_argument("--constitutions", required=True, help="Constitution JSON, ZIP, or directory")
    parser.add_argument("--target", default=cfg.TARGET_CONSTITUTION,
                        help="One constitution ID to target within the supplied pool")
    parser.add_argument("--existing", default="", help="Optional benchmark JSON, ZIP, or directory")
    parser.add_argument("--run-name", default=cfg.RUN_NAME)
    parser.add_argument("--run-dir", default="runs", help="Persistent run/checkpoint directory")
    parser.add_argument("--max-attempts", type=int, default=cfg.MAX_NEW_ATTEMPTS)
    parser.add_argument("--batch-size", type=int, default=cfg.GENERATION_BATCH_SIZE)
    parser.add_argument("--quota", type=int, default=cfg.SCENARIO_QUOTA)
    parser.add_argument("--min-criteria", type=int, default=cfg.MIN_DISTINCT_CRITERIA)
    args = parser.parse_args()

    cfg.CONSTITUTION_INPUT = args.constitutions
    cfg.TARGET_CONSTITUTION = args.target
    cfg.EXISTING_BANK_INPUT = args.existing
    cfg.RUN_NAME = args.run_name
    cfg.LOCAL_RUN_PARENT = str(Path(args.run_dir).expanduser())
    cfg.MAX_NEW_ATTEMPTS = args.max_attempts
    cfg.GENERATION_BATCH_SIZE = args.batch_size
    cfg.SCENARIO_QUOTA = args.quota
    cfg.MIN_DISTINCT_CRITERIA = args.min_criteria

    root, constitutions, bank = initialize_workspace()
    client = OpenRouterClient(root, obtain_openrouter_key())
    results = run_pipeline(root, constitutions, bank, client)
    show_coverage(results["report"])
    print(f"\nSelected additions: {len(results['selected'])}")
    print(f"Results: {results['archive']}")


if __name__ == "__main__":
    main()
