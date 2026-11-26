# Arabic answer generation

Answer and hybrid-search commands now default to `--domain all`: both labour and
companies, plus any future loaded domains. Use `--domain labour` or
`--domain companies` to restrict the scope. Source records include their domain;
article identity always includes its document ID. Existing embeddings are reused.

Simple requests such as `اعطني نص المادة رقم 5` use a direct article route.
If multiple eligible documents in the selected scope contain that number, output
has route=article_clarification, status=insufficient and clarification_options with
document titles/IDs/domains. It does not call Gemini. A unique match returns original
text directly (route=direct_article). This parser covers only simple whole-article
requests; it is not general conversational reference resolution or paragraph routing.
For an explicitly selected document use the existing exact command:
`python -m legal_rag.search --document 1211 --article 5 --domain all`.

1. Use the existing `GEMINI_API_KEY` in .env for both embedding and generation.
2. Optionally add `ANSWER_MODEL=gemini-3.5-flash-lite` (the code default).
   Keep database/embedding settings. GROQ_API_KEY is unused and may be removed.
3. Start the database and run:

```powershell
python -m legal_rag.answer "ما حقوق العاملة عند الولادة؟" --output answer-maternity.json
```

Open the JSON in VS Code. `answer` is the Arabic text, `claims` has per-point source
IDs, `sources` supplies cited original texts and URLs, and `retrieval` records the
hybrid candidates. Five retrieved articles need not mean five cited sources.
Possible status values are `answered`, `partial`, and `insufficient`.

Prompt version `arabic-evidence-v2` asks for direct corrections of false assumptions,
conditional application when personal facts are missing, specific clarification
questions, explicit calculation steps, and separate handling of unsupported parts.
`prompt_version` is saved with each output so old and new results can be compared.
Version `arabic-evidence-v3` additionally requires clarification of uncertain legal
categories (for example profit sharing versus commission employment) and distinguishes
end-of-service compensation from a pension. Rules for a category whose applicability
is unknown must be conditional, with missing facts and evidence gaps stated explicitly.
These are model instructions, not deterministic guarantees; re-evaluate real outputs.

Version `arabic-evidence-v4` makes clarification selective: complete, consistent
calculation inputs should receive an answered result based on those supplied inputs,
without invented worker-registration requirements or repeated wage questions.
Missing/contradictory inputs and unsupported net-deduction rules still need limits
or clarification. This remains prompt-based behavior, not an arithmetic engine.

This uses gemini-embedding-001 for the question, existing PostgreSQL document
vectors, and gemini-3.5-flash-lite for generation. No model downloads,
new packages or database migrations are required. Free-plan quotas still apply.

The prompt requires Arabic answers based only on the supplied full parent articles,
including conditions and exceptions. Empty retrieval skips generation. Irrelevant retrieval
is judged by the answering model; this is not a guaranteed out-of-domain detector.
JSON-schema generation, local schema checks and citation membership checks reject
malformed output, missing citations, invented source IDs and incomplete generations.
These checks do not prove that each claim follows from its cited article. Review
answers and test unsupported questions before using this as a public legal service.

Full source text is preserved. Context over 18000 characters is rejected rather than
silently cut; reduce `--limit` if needed. Gemini token/rate limits may still reject a
request below that character cap. Errors do not overwrite an existing output file.
Temporary HTTP 500/502/503/504 errors receive up to three generation retries after
approximately 2, 4 and 8 seconds plus random jitter. Retrieval and question embedding
are not repeated. Other errors, including quota error 429, stop without retrying.
Provider requests may incur usage if an earlier attempt was processed. Exhausted
retries stop with an error; no fallback answer is fabricated. Rerunning the entire
command makes fresh question and generation requests.

API references: https://ai.google.dev/gemini-api/docs/structured-output and
https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite.
