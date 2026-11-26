# Hybrid search

Default scope is now `all`: keyword and vector candidates are ranked jointly across
all loaded domains, including labour and companies. `--domain labour` or
`--domain companies` still restricts results. Other keyword/semantic CLIs retain
their previous default but accept `--domain all`. Both retrieval paths preserve
eligibility/model filters, and fused sources include the actual domain.

Start PostgreSQL using your existing project setup, then run from the project root:

```powershell
python -m legal_rag.hybrid_search "ما حقوق العاملة عند الولادة؟" --output hybrid-results.json
```

Open the output in VS Code. `results` contains up to five distinct source units.
Each has `full_article`, `source_url`, `keyword_rank`, `semantic_rank`, `rrf_score`
and separate `matches.keyword` / `matches.semantic` excerpts when available.

The command requests up to 20 candidates from each existing retriever. It converts
the question to a Gemini query embedding once and reuses stored document vectors.
Each method contributes `1 / (60 + rank)` per article, with equal weight. An article
found by both methods receives both contributions. Duplicates within a method count
once; ties are resolved by unit_id. Raw retrieval scores remain for inspection only.

For output limits above one, the top semantic candidate is retained if ordinary RRF
would discard it: it replaces the final selected result. This avoids losing a strong
semantic-only match solely because generic keyword matches appear in both lists.
RRF scores and original ranks remain unchanged; `preserve_semantic_best` records
this selection policy in the report. Single-result requests keep plain RRF behavior.
This is a recall safeguard, not a semantic correctness check or trained reranker;
the best vector match can still be irrelevant for an unsupported question.

Adjust pool/output sizes with `--candidates 30 --limit 5` (maximum 100 candidates,
and output limit must not exceed the pool size). An empty keyword result is allowed;
service failures stop the command rather than silently dropping a method.

No migration or re-embedding of documents is needed. Results are retrieved passages,
not generated answers. RRF scores are neither probabilities nor evidence of legal
correctness. Search may return loosely related passages for an unsupported question;
this step adds no calibrated relevance threshold or abstention mechanism.

Tests: `python -m unittest discover -s tests -p test_hybrid_search.py -v`.
