"""Curated evaluation dataset for The Reading Room RAG pipeline.

Contains representative benchmark queries across:
- Thematic / Semantic discovery (Computer Science, Data Mining, Multimedia, Philosophy, etc.)
- Specific book title lookups
- Specific author queries (leveraging hybrid author-boost)
- Out-of-scope & calculation queries (testing guardrail adherence & truthfulness)
"""

BENCHMARK_QUERIES: list[dict] = [
    # ── Category 1: Computer Science & Data Mining ────────────────────────────
    {
        "id": "q1",
        "category": "Data Mining",
        "query": "principles of data mining and knowledge discovery",
        "relevant_isbns": ["9783540410669", "026208290X", "9781846287657"],
        "expected_topics": ["data mining", "algorithms", "knowledge discovery"],
        "is_out_of_scope": False,
    },
    {
        "id": "q2",
        "category": "Data Warehousing",
        "query": "data warehousing and knowledge discovery proceedings",
        "relevant_isbns": ["9783540664581"],
        "expected_topics": ["data warehousing", "database"],
        "is_out_of_scope": False,
    },
    {
        "id": "q3",
        "category": "Neural Networks",
        "query": "artificial neural networks and computational intelligence",
        "relevant_isbns": ["8120312538", "9789812706249", "9788120332294"],
        "expected_topics": ["neural networks", "machine learning"],
        "is_out_of_scope": False,
    },

    # ── Category 2: Software Engineering & Systems ────────────────────────────
    {
        "id": "q4",
        "category": "Software Process",
        "query": "software process and engineering methodologies",
        "relevant_isbns": ["9783540655169", "3540661573", "3540658661"],
        "expected_topics": ["software process", "lifecycle"],
        "is_out_of_scope": False,
    },
    {
        "id": "q5",
        "category": "Workflow Management",
        "query": "workflow management systems for process organizations",
        "relevant_isbns": ["354065304X"],
        "expected_topics": ["workflow", "business processes"],
        "is_out_of_scope": False,
    },
    {
        "id": "q6",
        "category": "Conceptual Modeling",
        "query": "conceptual modeling for user interface design",
        "relevant_isbns": ["1852330090", "9783540659266"],
        "expected_topics": ["user interface", "modeling"],
        "is_out_of_scope": False,
    },
    {
        "id": "q7",
        "category": "Computer Networks",
        "query": "network design management and technical perspectives",
        "relevant_isbns": ["0849334047"],
        "expected_topics": ["networks", "management"],
        "is_out_of_scope": False,
    },

    # ── Category 3: Multimedia & Information Systems ─────────────────────────
    {
        "id": "q8",
        "category": "Multimedia Systems",
        "query": "multimedia information analysis and retrieval proceedings",
        "relevant_isbns": ["9783540648260", "1852332484", "9783540660828"],
        "expected_topics": ["multimedia", "retrieval", "audio video"],
        "is_out_of_scope": False,
    },
    {
        "id": "q9",
        "category": "Information Systems",
        "query": "visual information and information systems",
        "relevant_isbns": ["9783540660798"],
        "expected_topics": ["visual information", "imaging"],
        "is_out_of_scope": False,
    },

    # ── Category 4: Mathematics & Physics ─────────────────────────────────────
    {
        "id": "q10",
        "category": "Applied Mathematics",
        "query": "applied complex variables for scientists and engineers",
        "relevant_isbns": ["9780521004626"],
        "expected_topics": ["complex variables", "mathematics"],
        "is_out_of_scope": False,
    },
    {
        "id": "q11",
        "category": "Cosmology / Physics",
        "query": "brief history of time big bang to black holes",
        "relevant_isbns": ["0553176986", "9788179925911"],
        "expected_topics": ["cosmology", "black holes", "physics"],
        "is_out_of_scope": False,
    },

    # ── Category 5: Literature, Romance & History ────────────────────────────
    {
        "id": "q12",
        "category": "Romance / Human Relationships",
        "query": "tales of love passion and human erotic desire",
        "relevant_isbns": ["0195630262", "9780195643770"],
        "expected_topics": ["love", "passion", "human relationships"],
        "is_out_of_scope": False,
    },
    {
        "id": "q13",
        "category": "Indian History",
        "query": "history of early and ancient india",
        "relevant_isbns": ["0140138358", "9780140138368", "019564445X", "0195633423"],
        "expected_topics": ["india", "ancient history", "mauryas"],
        "is_out_of_scope": False,
    },
    {
        "id": "q14",
        "category": "Philosophy",
        "query": "oxford dictionary of philosophy",
        "relevant_isbns": ["0192831348", "9780198751656"],
        "expected_topics": ["philosophy", "dictionary"],
        "is_out_of_scope": False,
    },

    # ── Category 6: Hybrid Author Queries ─────────────────────────────────────
    {
        "id": "q15",
        "category": "Author Search",
        "query": "kakar sudhir",
        "relevant_isbns": ["0195630262", "9780195696684", "9780195615081"],
        "expected_topics": ["author lookup"],
        "is_out_of_scope": False,
    },
    {
        "id": "q16",
        "category": "Author Search",
        "query": "thapar romila",
        "relevant_isbns": ["0140138358", "019564445X", "9780195651775"],
        "expected_topics": ["indian history", "author lookup"],
        "is_out_of_scope": False,
    },

    # ── Category 7: Out-of-Scope & Guardrail Queries ──────────────────────────
    {
        "id": "q17",
        "category": "Math Guardrail",
        "query": "calculate 45 * 80 + 12",
        "relevant_isbns": [],
        "expected_topics": ["refusal"],
        "is_out_of_scope": True,
    },
    {
        "id": "q18",
        "category": "Math Guardrail",
        "query": "what is the derivative of x^3 + 2x^2 - 5?",
        "relevant_isbns": [],
        "expected_topics": ["refusal"],
        "is_out_of_scope": True,
    },
    {
        "id": "q19",
        "category": "General Knowledge Guardrail",
        "query": "who won the 2022 FIFA World Cup in football?",
        "relevant_isbns": [],
        "expected_topics": ["refusal"],
        "is_out_of_scope": True,
    },
    {
        "id": "q20",
        "category": "Math Guardrail",
        "query": "solve 1500 / 25",
        "relevant_isbns": [],
        "expected_topics": ["refusal"],
        "is_out_of_scope": True,
    },
]

