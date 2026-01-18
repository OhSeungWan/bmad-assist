#!/usr/bin/env python3
"""Benchmark data condenser for LLM analysis.

Reads benchmark YAML files and validation-mapping JSON files from a project,
condenses them into a compact format suitable for LLM analysis.

Supports two modes:
- project: Traditional single-project consolidation (default)
- experiments: Multi-fixture experiment consolidation

Usage:
    python benchmark-prepare.py -p ./my-project                    # -> docs/benchmark-summary-{ts}.json
    python benchmark-prepare.py -p ../scalper-ui -o custom.json    # -> custom.json
    python benchmark-prepare.py -p ./my-project --stdout           # -> stdout
    python benchmark-prepare.py -p ./my-project --mode experiments # -> per-fixture summaries
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Condense benchmark data for LLM analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python benchmark-prepare.py -p ./my-project
    python benchmark-prepare.py -p ../scalper-ui -o summary.json
    python benchmark-prepare.py -p ./my-project --mode experiments
        """,
    )
    parser.add_argument(
        "-p", "--project",
        type=Path,
        required=True,
        help="Path to project root",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file (default: {project}/docs/benchmark-summary-{timestamp}.json)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Output to stdout instead of file",
    )
    parser.add_argument(
        "--mode",
        choices=["project", "experiments"],
        default="project",
        help="Operating mode (default: project)",
    )
    parser.add_argument(
        "--experiments-dir",
        type=Path,
        help="Base directory for experiments mode (default: same as --project)",
    )

    args = parser.parse_args()

    project_path = args.project.resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    # Determine base directory for experiments mode
    base_dir = args.experiments_dir.resolve() if args.experiments_dir else project_path

    try:
        from bmad_assist.experiments.prepare import BenchmarkPreparer
    except ImportError as e:
        print(f"Error: Failed to import BenchmarkPreparer: {e}", file=sys.stderr)
        print("Make sure bmad-assist is installed: pip install -e .", file=sys.stderr)
        return 1

    try:
        preparer = BenchmarkPreparer(base_dir, mode=args.mode)

        if args.mode == "project":
            result = preparer.prepare_project(args.output, args.stdout)
            if not args.stdout:
                print(f"Benchmark summary generated: {result.output_path}", file=sys.stderr)
                print(f"  Stories: {result.runs_processed}", file=sys.stderr)
                print(f"  Evals: {result.evals_count}", file=sys.stderr)
                print(f"  Total time: {result.total_time_minutes} min", file=sys.stderr)
                print(f"  Models: {', '.join(result.models)}", file=sys.stderr)
        else:
            results = preparer.prepare_experiments(args.output)
            if not results:
                print("Warning: No experiment runs found", file=sys.stderr)
                return 0

            print(f"Processed {len(results)} fixtures:", file=sys.stderr)
            for fixture, result in results.items():
                print(f"  {fixture}:", file=sys.stderr)
                print(f"    Output: {result.output_path}", file=sys.stderr)
                print(f"    Runs: {result.runs_processed}", file=sys.stderr)
                print(f"    Evals: {result.evals_count}", file=sys.stderr)
                print(f"    Time: {result.total_time_minutes} min", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
