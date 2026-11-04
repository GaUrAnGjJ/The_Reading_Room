#!/usr/bin/env python3
"""CLI evaluation script for The Reading Room RAG & Recommender system.

Usage:
    python evaluate.py
    python evaluate.py --k 1 3 5 --output evaluation/results
    python evaluate.py --no-judge
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.dataset import BENCHMARK_QUERIES
from evaluation.evaluator import RAGEvaluator


def main():
    parser = argparse.ArgumentParser(
        description="Run RAG evaluation: Precision@K, Recall@K, MRR, and Truthfulness"
    )
    parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        default=[1, 3, 5],
        help="K cut-off values for Precision@K and Recall@K (default: 1 3 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of benchmark queries to run",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Disable Groq LLM-as-a-judge and use deterministic rule-based grounding",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation/results",
        help="Output directory for JSON and Markdown reports (default: evaluation/results)",
    )

    args = parser.parse_args()

    dataset = BENCHMARK_QUERIES
    if args.limit:
        dataset = dataset[: args.limit]

    evaluator = RAGEvaluator(
        k_list=args.k,
        use_llm_judge=not args.no_judge,
    )

    summary = evaluator.run_benchmark(
        dataset=dataset,
        save_results=True,
        output_dir=args.output,
    )

    agg = summary["aggregate_metrics"]
    print("\n" + "=" * 55)
    print("           BENCHMARK EVALUATION SUMMARY")
    print("=" * 55)
    for k in sorted(args.k):
        print(f"  Precision@{k:<2}       : {agg.get(f'mean_precision@{k}', 0.0) * 100:>6.2f}%")
        print(f"  Recall@{k:<2}          : {agg.get(f'mean_recall@{k}', 0.0) * 100:>6.2f}%")
    print(f"  Mean Reciprocal Rank : {agg.get('MRR', 0.0):>7.4f}")
    print(f"  Truthfulness Score   : {agg.get('mean_truthfulness', 0.0) * 100:>6.2f}%")
    print(f"  Citation Accuracy    : {agg.get('mean_citation_accuracy', 0.0) * 100:>6.2f}%")
    print(f"  Guardrail Accuracy   : {agg.get('guardrail_accuracy', 0.0) * 100:>6.2f}%")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()

