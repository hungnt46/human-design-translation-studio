# Split Long Source

Split the requested source document according to the chunking rules in `AGENTS.md`.

Do not translate anything.

Requirements:
- preserve every source word;
- preserve original order;
- create no overlap;
- create no duplicate content;
- omit nothing;
- standard chunks: 1,500–1,600 source words;
- hard maximum: 1,600 source words;
- final remainder chunk may be shorter;
- never split inside a sentence.
- never treat PDF/OCR hard wrapping or a blank line alone as a semantic boundary;
- keep multi-line sentences, titles, footnotes, table rows, and index entries intact;
- if no safe boundary exists in the target range, use the latest safe boundary below 1,500 and warn rather than cutting an idea.

Within the permitted range, prefer:

section boundary > subsection boundary > genuine paragraph boundary > sentence boundary > standalone structural item.

Use `scripts/split_source.py` when practical rather than estimating word count manually.

Write chunks to:

`work/<document_id>/source_chunks/`

using:

`chunk_001.md`
`chunk_002.md`
...

Create or update:

`work/<document_id>/manifest.yaml`

Then validate the split with `scripts/check_chunks.py`.

Validation must fail if any adjacent chunks appear to continue the same sentence or structural idea.

Do not modify the original source.
