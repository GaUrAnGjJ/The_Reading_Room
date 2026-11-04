# 📊 RAG & Information Retrieval Evaluation Report

**Generated:** `2026-11-04 21:20:02`  
**Total Benchmark Queries:** `20` (`16` in-domain, `4` guardrail)  

---

## 🎯 Executive Metric Summary

| Evaluation Metric | Score | Description |
|---|:---:|---|
| **Precision@1** | `62.5%` | Proportion of top-1 retrieved books that are relevant |
| **Recall@1** | `32.8%` | Proportion of all relevant catalog books retrieved in top-1 |
| **Precision@3** | `33.3%` | Proportion of top-3 retrieved books that are relevant |
| **Recall@3** | `57.8%` | Proportion of all relevant catalog books retrieved in top-3 |
| **Precision@5** | `25.0%` | Proportion of top-5 retrieved books that are relevant |
| **Recall@5** | `65.6%` | Proportion of all relevant catalog books retrieved in top-5 |
| **Mean Reciprocal Rank (MRR)** | `0.781` | Average reciprocal rank of the first relevant book retrieved |
| **Truthfulness / Faithfulness** | `100.0%` | Proportion of claims & recommendations strictly grounded in catalog |
| **Citation Accuracy** | `100.0%` | Accuracy of cited titles/authors without hallucinating external titles |
| **Guardrail Adherence** | `100.0%` | Strict rejection of off-topic & calculation requests |

---

## 📋 Detailed Query Breakdown

| # | Query | Category | P@1 | P@3 | P@5 | RR | Truthfulness | Status |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `principles of data mining and knowledge discovery` | Data Mining | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | ✅ Pass |
| 2 | `data warehousing and knowledge discovery proceedings` | Data Warehousing | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | ✅ Pass |
| 3 | `artificial neural networks and computational intelligence` | Neural Networks | 0.00 | 0.00 | 0.20 | 0.25 | 1.00 | ✅ Pass |
| 4 | `software process and engineering methodologies` | Software Process | 0.00 | 0.00 | 0.20 | 0.25 | 1.00 | ✅ Pass |
| 5 | `workflow management systems for process organizations` | Workflow Management | 0.00 | 0.33 | 0.20 | 0.50 | 1.00 | ✅ Pass |
| 6 | `conceptual modeling for user interface design` | Conceptual Modeling | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | ✅ Pass |
| 7 | `network design management and technical perspectives` | Computer Networks | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | ✅ Pass |
| 8 | `multimedia information analysis and retrieval proceedings` | Multimedia Systems | 0.00 | 0.33 | 0.20 | 0.50 | 1.00 | ✅ Pass |
| 9 | `visual information and information systems` | Information Systems | 0.00 | 0.33 | 0.20 | 0.50 | 1.00 | ✅ Pass |
| 10 | `applied complex variables for scientists and engineers` | Applied Mathematics | 0.00 | 0.33 | 0.20 | 0.50 | 1.00 | ✅ Pass |
| 11 | `brief history of time big bang to black holes` | Cosmology / Physics | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | ✅ Pass |
| 12 | `tales of love passion and human erotic desire` | Romance / Human Relationships | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | ✅ Pass |
| 13 | `history of early and ancient india` | Indian History | 1.00 | 0.33 | 0.40 | 1.00 | 1.00 | ✅ Pass |
| 14 | `oxford dictionary of philosophy` | Philosophy | 1.00 | 0.33 | 0.20 | 1.00 | 1.00 | ✅ Pass |
| 15 | `kakar sudhir` | Author Search | 1.00 | 0.67 | 0.40 | 1.00 | 1.00 | ✅ Pass |
| 16 | `thapar romila` | Author Search | 1.00 | 0.67 | 0.60 | 1.00 | 1.00 | ✅ Pass |
| 17 | `calculate 45 * 80 + 12` | Math Guardrail | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | ✅ Pass |
| 18 | `what is the derivative of x^3 + 2x^2 - 5?` | Math Guardrail | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | ✅ Pass |
| 19 | `who won the 2022 FIFA World Cup in football?` | General Knowledge Guardrail | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | ✅ Pass |
| 20 | `solve 1500 / 25` | Math Guardrail | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | ✅ Pass |

---

## 🔬 Methodology & Definitions

1. **Precision@K**: Measures the signal-to-noise ratio in the top $K$ recommendations: $\frac{|\text{Retrieved}_K \cap \text{Relevant}|}{K}$.
2. **Recall@K**: Measures catalog coverage: $\frac{|\text{Retrieved}_K \cap \text{Relevant}|}{|\text{Relevant}|}$.
3. **MRR (Mean Reciprocal Rank)**: Evaluates ranking position of the very first hit: $\frac{1}{|Q|}\sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$.
4. **Truthfulness / Faithfulness**: Evaluates whether the generated LLM text makes ungrounded claims or mentions books that do not exist in the retrieved context block.