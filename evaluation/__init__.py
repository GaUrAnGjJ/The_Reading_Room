"""RAG and Information Retrieval evaluation package for The Reading Room."""

from .metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    compute_retrieval_metrics,
    evaluate_truthfulness,
)
from .dataset import BENCHMARK_QUERIES
from .evaluator import RAGEvaluator

__all__ = [
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "compute_retrieval_metrics",
    "evaluate_truthfulness",
    "BENCHMARK_QUERIES",
    "RAGEvaluator",
]

