# Adding another legal field

Labour embeddings are available; future fields still require their own preparation
and embedding generation. These are instructions, not a statement that new source
files have already been supplied or verified.

1. Place the reviewed corpus in data/corpus/<domain>/ with legislation.jsonl and
   units.jsonl in the existing format. Inventory originals, amendments, repealed
   texts, jurisdiction, source links, attachments and verification flags. Do not
   assume a website subject category contains every relevant law.
2. Check Maqam IDs and unit IDs against existing domains. Article numbers can
   repeat safely across documents: maqam:<document_id>:art:<article_no> is the identity.
   Legislation Maqam IDs are global database keys; the same document cannot simply
   be duplicated under multiple domains. Cross-field shared documents need deliberate
   handling; do not overwrite or invent IDs to work around a conflict.
3. Apply pending migrations, load the domain, preview and write chunks. Reloading
   a domain replaces its source rows and removes derived chunks. Rebuild afterward.
4. Review chunk warnings/holds and token counts. Generate vectors only for eligible
   inputs. Cache reuse skips identical inputs under the same complete model profile.
5. Evaluate known-answer, multiple-article and unsupported questions for the new
   field before treating it as supported. Search and answer with --domain explicitly.

Example using company as a PLACEHOLDER domain (run only after supplying its corpus):

```powershell
python -m legal_rag.migrate
python -m legal_rag.load data/corpus/company
python -m legal_rag.chunk --domain company --preview
python -m legal_rag.chunk --domain company --write
python -m legal_rag.validate_tokens --domain company --model gemini-embedding-001 --output token-report-company.json
python -m legal_rag.embed --domain company --limit 5
python -m legal_rag.embed --domain company --limit 5 --write
python -m legal_rag.embed --domain company --write
python -m legal_rag.answer "كيف أسجل شركة تجارية؟" --domain company --output answer-company.json
```

Do not copy labour's --expect-searchable 405 to another field. Derive and verify its
own expected coverage. Unchanged labour vectors need not be generated again. The
fixed 1536-dimensional storage supports the current embedding profile; changing
embedding models/dimensions needs a separate migration/re-embedding plan.
