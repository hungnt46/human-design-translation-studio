# Assemble Complete Translation

Assemble the translated chunks for the requested document.

Read:
- `AGENTS.md`;
- the document manifest;
- all translated chunks in numerical order.

Before assembly verify:
- every expected chunk exists;
- every chunk has passed translation QA;
- no chunk is duplicated;
- no chunk is missing.

Assemble exactly once in source order.

Do not summarize or rewrite the chunks during assembly.

Remove chunk-only metadata that is not part of the original document.

Preserve original headings and meaningful structure.

After assembly perform a complete document-level QA for:
- omissions;
- duplicated passages;
- broken transitions at chunk boundaries;
- terminology drift;
- speaker-label inconsistency;
- altered modality or certainty;
- names, numbers, identifiers, units, formulas, code, and technical references;
- translationese or source-language interference;
- inconsistent target-language phrasing.

Write the final result to `translations/<target-language-code>/`.

Do not delete work files automatically.
