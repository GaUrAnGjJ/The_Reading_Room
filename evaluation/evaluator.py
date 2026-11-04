"""RAG evaluation orchestrator for The Reading Room."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from chat.chatbot import chat as rag_chat
from recommender.recommender import BookRecommender
from evaluation.dataset import BENCHMARK_QUERIES
from evaluation.metrics import compute_retrieval_metrics, evaluate_truthfulness

try:
    from groq import Groq
except ImportError:
    Groq = None

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Automated evaluation suite for Retrieval (P@K, R@K, MRR) and Generation (Truthfulness)."""

    def __init__(
        self,
        recommender: BookRecommender | None = None,
        k_list: list[int] = [1, 3, 5],
        use_llm_judge: bool = True,
        judge_model: str = "openai/gpt-oss-20b",
    ):
        self.k_list = sorted(k_list)
        self.max_k = max(self.k_list) if self.k_list else 5
        self.use_llm_judge = use_llm_judge
        self.judge_model = judge_model

        # Load recommender
        if recommender is not None:
            self.recommender = recommender
        else:
            self.recommender = BookRecommender()
            self.recommender.load()

        # Initialize Groq client for LLM-as-a-judge if key exists
        self.groq_client = None
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if self.use_llm_judge and api_key and Groq is not None:
            try:
                self.groq_client = Groq(api_key=api_key)
            except Exception as e:
                logger.warning("Could not initialize Groq client: %s", e)

    def evaluate_query(self, test_case: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single test case for both retrieval and generation."""
        query = test_case["query"]
        relevant_isbns = test_case.get("relevant_isbns", [])
        is_out_of_scope = test_case.get("is_out_of_scope", False)

        t0 = time.time()

        # ── 1. Retrieval Phase ────────────────────────────────────────────────
        retrieved_books = self.recommender.recommend(query, top_k=self.max_k)
        retrieved_isbns = [b.get("isbn", "") for b in retrieved_books]

        retrieval_metrics = {}
        if not is_out_of_scope and relevant_isbns:
            retrieval_metrics = compute_retrieval_metrics(
                retrieved_isbns=retrieved_isbns,
                relevant_isbns=relevant_isbns,
                k_list=self.k_list,
            )
        else:
            # For out-of-scope, retrieval metrics are not applicable
            for k in self.k_list:
                retrieval_metrics[f"precision@{k}"] = 1.0 if not retrieved_isbns else 0.0
                retrieval_metrics[f"recall@{k}"] = 1.0
            retrieval_metrics["reciprocal_rank"] = 1.0 if is_out_of_scope else 0.0

        # ── 2. Generation & RAG Phase ─────────────────────────────────────────
        chat_result = rag_chat(
            message=query,
            history=[],
            recommender=self.recommender,
        )
        response_text = chat_result.get("reply") or chat_result.get("response") or ""
        context_books = chat_result.get("books", [])

        # ── 3. Truthfulness & Faithfulness Evaluation ─────────────────────────
        truth_eval = evaluate_truthfulness(
            query=query,
            response=response_text,
            context_books=context_books,
            is_out_of_scope=is_out_of_scope,
            groq_client=self.groq_client,
            judge_model=self.judge_model,
        )

        latency_sec = time.time() - t0

        return {
            "id": test_case.get("id"),
            "category": test_case.get("category"),
            "query": query,
            "is_out_of_scope": is_out_of_scope,
            "relevant_isbns": relevant_isbns,
            "retrieved_isbns": retrieved_isbns,
            "retrieved_titles": [b.get("title", "") for b in retrieved_books],
            "retrieval_metrics": retrieval_metrics,
            "response": response_text,
            "truthfulness": truth_eval,
            "latency_seconds": round(latency_sec, 2),
        }

    def run_benchmark(
        self,
        dataset: list[dict[str, Any]] | None = None,
        save_results: bool = True,
        output_dir: str | Path = "evaluation/results",
    ) -> dict[str, Any]:
        """Run the complete evaluation benchmark and aggregate metrics."""
        dataset = dataset or BENCHMARK_QUERIES
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n========================================================")
        print(f"  RUNNING RAG EVALUATION BENCHMARK ({len(dataset)} queries)")
        print(f"  K thresholds: {self.k_list}")
        print(f"  LLM Judge: {'Enabled' if self.groq_client else 'Rule-based'}")
        print(f"========================================================\n")

        query_results = []
        for i, test_case in enumerate(dataset, 1):
            sys.stdout.write(f"[{i:02d}/{len(dataset):02d}] Evaluating: \"{test_case['query'][:38]}...\" ")
            sys.stdout.flush()
            res = self.evaluate_query(test_case)
            query_results.append(res)
            
            p3 = res["retrieval_metrics"].get("precision@3", 0.0)
            rr = res["retrieval_metrics"].get("reciprocal_rank", 0.0)
            truth = res["truthfulness"]["truthfulness_score"]
            print(f"-> P@3: {p3:.2f} | RR: {rr:.2f} | Truth: {truth:.2f}")

        # ── Aggregate Statistics ──────────────────────────────────────────────
        in_scope_results = [r for r in query_results if not r["is_out_of_scope"]]
        out_scope_results = [r for r in query_results if r["is_out_of_scope"]]

        agg_metrics: dict[str, Any] = {
            "total_queries": len(query_results),
            "in_scope_queries": len(in_scope_results),
            "out_of_scope_queries": len(out_scope_results),
        }

        # Retrieval averages (on in-scope queries with ground truth)
        if in_scope_results:
            for k in self.k_list:
                agg_metrics[f"mean_precision@{k}"] = round(
                    sum(r["retrieval_metrics"][f"precision@{k}"] for r in in_scope_results) / len(in_scope_results),
                    4,
                )
                agg_metrics[f"mean_recall@{k}"] = round(
                    sum(r["retrieval_metrics"][f"recall@{k}"] for r in in_scope_results) / len(in_scope_results),
                    4,
                )
            
            # Mean Reciprocal Rank (MRR)
            agg_metrics["MRR"] = round(
                sum(r["retrieval_metrics"]["reciprocal_rank"] for r in in_scope_results) / len(in_scope_results),
                4,
            )
        else:
            for k in self.k_list:
                agg_metrics[f"mean_precision@{k}"] = 0.0
                agg_metrics[f"mean_recall@{k}"] = 0.0
            agg_metrics["MRR"] = 0.0

        # Generation Truthfulness averages (across all queries)
        agg_metrics["mean_truthfulness"] = round(
            sum(r["truthfulness"]["truthfulness_score"] for r in query_results) / len(query_results),
            4,
        )
        agg_metrics["mean_citation_accuracy"] = round(
            sum(r["truthfulness"]["citation_accuracy"] for r in query_results) / len(query_results),
            4,
        )

        # Guardrail adherence
        if out_scope_results:
            guardrail_acc = sum(r["truthfulness"]["truthfulness_score"] for r in out_scope_results) / len(out_scope_results)
            agg_metrics["guardrail_accuracy"] = round(guardrail_acc, 4)
        else:
            agg_metrics["guardrail_accuracy"] = 1.0

        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "aggregate_metrics": agg_metrics,
            "query_details": query_results,
        }

        if save_results:
            json_path = output_dir / "evaluation_report.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)

            md_path = output_dir / "evaluation_report.md"
            self._write_markdown_report(summary, md_path)

            print(f"\n[OK] Reports saved to:")
            print(f"     JSON: {json_path}")
            print(f"     MD:   {md_path}")

        return summary

    def _write_markdown_report(self, summary: dict[str, Any], path: Path) -> None:
        """Generate a GitHub Flavored Markdown report."""
        agg = summary["aggregate_metrics"]
        queries = summary["query_details"]

        lines = [
            "# 📊 RAG & Information Retrieval Evaluation Report",
            "",
            f"**Generated:** `{summary['timestamp']}`  ",
            f"**Total Benchmark Queries:** `{agg['total_queries']}` (`{agg['in_scope_queries']}` in-domain, `{agg['out_of_scope_queries']}` guardrail)  ",
            "",
            "---",
            "",
            "## 🎯 Executive Metric Summary",
            "",
            "| Evaluation Metric | Score | Description |",
            "|---|:---:|---|",
        ]

        for k in self.k_list:
            lines.append(f"| **Precision@{k}** | `{agg.get(f'mean_precision@{k}', 0.0) * 100:.1f}%` | Proportion of top-{k} retrieved books that are relevant |")
            lines.append(f"| **Recall@{k}** | `{agg.get(f'mean_recall@{k}', 0.0) * 100:.1f}%` | Proportion of all relevant catalog books retrieved in top-{k} |")

        lines.extend([
            f"| **Mean Reciprocal Rank (MRR)** | `{agg.get('MRR', 0.0):.3f}` | Average reciprocal rank of the first relevant book retrieved |",
            f"| **Truthfulness / Faithfulness** | `{agg.get('mean_truthfulness', 0.0) * 100:.1f}%` | Proportion of claims & recommendations strictly grounded in catalog |",
            f"| **Citation Accuracy** | `{agg.get('mean_citation_accuracy', 0.0) * 100:.1f}%` | Accuracy of cited titles/authors without hallucinating external titles |",
            f"| **Guardrail Adherence** | `{agg.get('guardrail_accuracy', 0.0) * 100:.1f}%` | Strict rejection of off-topic & calculation requests |",
            "",
            "---",
            "",
            "## 📋 Detailed Query Breakdown",
            "",
            "| # | Query | Category | P@1 | P@3 | P@5 | RR | Truthfulness | Status |",
            "|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|",
        ])

        for i, q in enumerate(queries, 1):
            rm = q["retrieval_metrics"]
            p1 = rm.get("precision@1", 0.0)
            p3 = rm.get("precision@3", 0.0)
            p5 = rm.get("precision@5", 0.0)
            rr = rm.get("reciprocal_rank", 0.0)
            truth = q["truthfulness"]["truthfulness_score"]
            status = "✅ Pass" if truth >= 0.7 and (q["is_out_of_scope"] or rr > 0.0) else "⚠️ Review"

            lines.append(
                f"| {i} | `{q['query']}` | {q['category']} | {p1:.2f} | {p3:.2f} | {p5:.2f} | {rr:.2f} | {truth:.2f} | {status} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 🔬 Methodology & Definitions",
            "",
            "1. **Precision@K**: Measures the signal-to-noise ratio in the top $K$ recommendations: $\\frac{|\\text{Retrieved}_K \\cap \\text{Relevant}|}{K}$.",
            "2. **Recall@K**: Measures catalog coverage: $\\frac{|\\text{Retrieved}_K \\cap \\text{Relevant}|}{|\\text{Relevant}|}$.",
            "3. **MRR (Mean Reciprocal Rank)**: Evaluates ranking position of the very first hit: $\\frac{1}{|Q|}\\sum_{i=1}^{|Q|} \\frac{1}{\\text{rank}_i}$.",
            "4. **Truthfulness / Faithfulness**: Evaluates whether the generated LLM text makes ungrounded claims or mentions books that do not exist in the retrieved context block.",
        ])

        path.write_text("\n".join(lines), encoding="utf-8")

