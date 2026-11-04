"""Evaluation metrics for RAG and Information Retrieval.

Metrics implemented:
- Precision@K: Fraction of top-K retrieved documents that are relevant.
- Recall@K: Fraction of all relevant documents captured in top-K.
- MRR (Mean Reciprocal Rank): 1 / rank of the first relevant retrieved document.
- Truthfulness / Faithfulness: Quantitative assessment (0.0 - 1.0) of whether
  claims and book references in the generated answer are strictly grounded in
  the retrieved context without hallucination.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable

logger = logging.getLogger(__name__)


# ── Retrieval Metrics ─────────────────────────────────────────────────────────

def precision_at_k(retrieved: list[str], relevant: Iterable[str], k: int) -> float:
    """Compute Precision@K.

    Formula:
        Precision@K = |Retrieved[:k] ∩ Relevant| / k

    Args:
        retrieved: Ordered list of retrieved document identifiers (e.g., ISBNs).
        relevant: Collection of ground-truth relevant document identifiers.
        k: Cut-off rank.

    Returns:
        Float in [0.0, 1.0].
    """
    if k <= 0:
        return 0.0
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0

    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / float(k)


def recall_at_k(retrieved: list[str], relevant: Iterable[str], k: int) -> float:
    """Compute Recall@K.

    Formula:
        Recall@K = |Retrieved[:k] ∩ Relevant| / |Relevant|

    Args:
        retrieved: Ordered list of retrieved document identifiers.
        relevant: Collection of ground-truth relevant document identifiers.
        k: Cut-off rank.

    Returns:
        Float in [0.0, 1.0].
    """
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0

    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / float(len(relevant_set))


def reciprocal_rank(retrieved: list[str], relevant: Iterable[str], k: int | None = None) -> float:
    """Compute Reciprocal Rank (RR).

    Formula:
        RR = 1 / rank_first_hit (1-indexed), or 0.0 if not found in top-K.

    Args:
        retrieved: Ordered list of retrieved document identifiers.
        relevant: Collection of ground-truth relevant document identifiers.
        k: Optional cut-off rank to search within.

    Returns:
        Float in [0.0, 1.0].
    """
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0

    search_items = retrieved[:k] if k is not None else retrieved
    for rank, item in enumerate(search_items, start=1):
        if item in relevant_set:
            return 1.0 / float(rank)
    return 0.0


def compute_retrieval_metrics(
    retrieved_isbns: list[str],
    relevant_isbns: Iterable[str],
    k_list: list[int] = [1, 3, 5],
) -> dict[str, float]:
    """Compute a suite of retrieval metrics for a single query.

    Args:
        retrieved_isbns: Ranked list of retrieved ISBNs from the recommender.
        relevant_isbns: Ground-truth relevant ISBNs.
        k_list: List of K thresholds to evaluate (default [1, 3, 5]).

    Returns:
        Dictionary of metric names to values.
    """
    results: dict[str, float] = {}
    for k in k_list:
        results[f"precision@{k}"] = precision_at_k(retrieved_isbns, relevant_isbns, k)
        results[f"recall@{k}"] = recall_at_k(retrieved_isbns, relevant_isbns, k)

    # Reciprocal rank using max K
    max_k = max(k_list) if k_list else len(retrieved_isbns)
    results["reciprocal_rank"] = reciprocal_rank(retrieved_isbns, relevant_isbns, k=max_k)
    return results


# ── Truthfulness & Faithfulness Evaluation ───────────────────────────────────

def check_citation_grounding(response_text: str, context_books: list[dict]) -> tuple[float, list[str]]:
    """Verify that titles mentioned in the response exist in the retrieved context.

    Returns:
        Tuple of (citation_accuracy_score in [0.0, 1.0], list of ungrounded titles).
    """
    if not context_books:
        # If no context was provided, any recommendation is ungrounded
        return 0.0, ["Response produced recommendations without retrieved context"]

    # Extract catalog titles (normalized lowercase)
    catalog_titles = [b.get("title", "").strip().lower() for b in context_books if b.get("title")]

    # Find quoted titles or pattern [1] "Title" in the LLM response
    quoted = re.findall(r'["“]([^"”]+)["”]', response_text)
    if not quoted:
        # Check if response refused or indicated no books found
        if any(w in response_text.lower() for w in ["do not contain", "could not find", "no books found"]):
            return 1.0, []
        return 1.0, []

    ungrounded = []
    grounded_count = 0

    for title in quoted:
        norm = title.strip().lower()
        # Exclude common conversational quotes (e.g., "Why it fits:")
        if len(norm) < 4 or norm in {"why it fits", "the reading room", "books referenced"}:
            continue

        is_present = any(norm in c_title or c_title in norm for c_title in catalog_titles)
        if is_present:
            grounded_count += 1
        else:
            ungrounded.append(title)

    total_checked = grounded_count + len(ungrounded)
    if total_checked == 0:
        return 1.0, []

    accuracy = grounded_count / float(total_checked)
    return accuracy, ungrounded


def evaluate_truthfulness(
    query: str,
    response: str,
    context_books: list[dict],
    is_out_of_scope: bool = False,
    groq_client: Any | None = None,
    judge_model: str = "openai/gpt-oss-20b",
) -> dict[str, Any]:
    """Calculate the Truthfulness / Faithfulness score of the RAG response.

    Truthfulness evaluates whether all statements, claims, and book references
    in the response are faithfully supported by the retrieved catalog context
    and free of hallucinations.

    Args:
        query: The user query.
        response: The generated RAG response text.
        context_books: List of book metadata dictionaries provided as context.
        is_out_of_scope: Flag if the query was intentionally out of scope / math.
        groq_client: Optional Groq client for LLM-as-a-judge evaluation.
        judge_model: Groq model name for judging.

    Returns:
        Dict containing:
            - truthfulness_score: float in [0.0, 1.0]
            - citation_accuracy: float in [0.0, 1.0]
            - ungrounded_entities: list of strings
            - reasoning: explanation string
            - method: 'llm_judge' or 'rule_based_grounding'
    """
    clean_resp = response.strip()

    # Case 1: Out of scope / guardrail queries
    if is_out_of_scope:
        refusal_phrases = [
            "do not contain this information",
            "specialized book assistant",
            "could not find",
            "only answer questions or provide recommendations based on the books",
        ]
        is_refusal = any(p in clean_resp.lower() for p in refusal_phrases)
        return {
            "truthfulness_score": 1.0 if is_refusal else 0.0,
            "citation_accuracy": 1.0,
            "ungrounded_entities": [],
            "reasoning": "Correctly rejected out-of-scope query without hallucination." if is_refusal else "Failed to reject out-of-scope query; hallucinated response.",
            "method": "guardrail_verification",
        }

    # Case 2: Citation grounding check
    cite_acc, ungrounded = check_citation_grounding(clean_resp, context_books)

    # Case 3: LLM-as-a-judge (if Groq client available)
    if groq_client is not None:
        try:
            # Build condensed context representation
            context_summary = []
            for i, b in enumerate(context_books, 1):
                t = b.get("title", "Unknown")
                a = b.get("author", "Unknown")
                d = (b.get("description") or "")[:250]
                context_summary.append(f"Book {i}: \"{t}\" by {a}. Overview: {d}")
            context_str = "\n".join(context_summary) if context_summary else "No books in context."

            judge_prompt = f"""You are an objective evaluation judge auditing an AI book recommendation assistant for Faithfulness and Truthfulness.

[Retrieved Catalog Context]:
{context_str}

[User Query]:
{query}

[Assistant Response]:
{clean_resp}

Task:
Evaluate whether the assistant's response is completely truthful and strictly grounded in the Retrieved Catalog Context.
Check:
1. Did the assistant recommend ANY book or author not listed in the retrieved context? (Hallucination penalty)
2. Are facts/themes cited in the description supported by the context?
3. If the query could not be satisfied, did the assistant truthfully state so?

Respond with a JSON object in this exact format:
{{
  "truthfulness_score": <float between 0.0 and 1.0>,
  "reasoning": "<1-2 sentence explanation>"
}}
JSON output only.
"""
            completion = groq_client.chat.completions.create(
                model=judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0.1,
                max_tokens=200,
            )
            raw_text = completion.choices[0].message.content.strip()
            # Extract JSON block
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                llm_score = float(data.get("truthfulness_score", 1.0))
                llm_score = max(0.0, min(1.0, llm_score))
                
                # Combine LLM judgment with hard citation check
                final_score = min(llm_score, cite_acc)
                return {
                    "truthfulness_score": round(final_score, 3),
                    "citation_accuracy": round(cite_acc, 3),
                    "ungrounded_entities": ungrounded,
                    "reasoning": data.get("reasoning", "Evaluated via LLM judge."),
                    "method": "llm_judge",
                }
        except Exception as e:
            logger.warning("LLM-as-a-judge failed (%s). Falling back to rule-based grounding.", e)

    # Fallback Case 4: Deterministic rule-based grounding
    # Penalize for ungrounded citations or empty responses
    if not clean_resp:
        return {
            "truthfulness_score": 0.0,
            "citation_accuracy": 0.0,
            "ungrounded_entities": [],
            "reasoning": "Empty assistant response.",
            "method": "rule_based_grounding",
        }

    truth_score = cite_acc
    reason = (
        f"All cited titles are verified in retrieved context."
        if not ungrounded
        else f"Response cited ungrounded titles: {ungrounded}"
    )

    return {
        "truthfulness_score": round(truth_score, 3),
        "citation_accuracy": round(cite_acc, 3),
        "ungrounded_entities": ungrounded,
        "reasoning": reason,
        "method": "rule_based_grounding",
    }

