# ADR-0002: Retrieval — in-repo BM25 (Okapi) over policy chunks

Status: Proposed (Stage 0 gate)

## Context
Section 0.1 forbids a second model, including an embedding model, unless an ADR approves it. The corpus is small (40 synthetic policy docs). Retrieval has to be deterministic, cheap, and able to take a per-scenario overlay document for the poisoned-policy surface.

## Decision
- Okapi BM25 (k1 = 1.5, b = 0.75), implemented in about 80 lines of standard-library Python. No `rank_bm25` dependency.
- Chunking: split by markdown heading, cap of about 120 words per chunk. Chunk IDs are `doc_id#n`.
- Tokenizer: Unicode NFKC, lowercase, split on `\W+` with Devanagari letters and combining marks kept inside tokens, plus a small stopword list per language. Ties are broken by chunk ID so the ranking is stable.
- Policy docs are written in English, with key terms carrying Hindi/Hinglish aliases in a `keywords:` front-matter line. This partly bridges Hindi-script queries.
- The ContextBuilder pre-retrieves the top 2 chunks for the customer message. The model can also call `search_policy` (top 3).
- Overlay: a scenario can add documents to the index for that scenario only (poisoned-document surface). The overlay is rebuilt per scenario and never persisted.

## Consequences
- Lexical retrieval is weaker for Devanagari and romanized-Hindi queries against English docs. Retrieval hit rate gets reported per language in Stage 3/5, so a language gap can be traced to retrieval rather than injection.
- No embeddings means no second model and no extra VRAM.
