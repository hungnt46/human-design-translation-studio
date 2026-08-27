# Translate Complete File

Translate the requested source file from beginning to end according to `AGENTS.md`.

## Required preparation

Before translating:

1. Read `AGENTS.md`.
2. Read `glossary/GLOSSARY.md`.
3. Read only the domain glossaries relevant to the source, if any.
4. Read relevant entries from `glossary/TERM_DECISIONS.md`.
5. Consult `reference/APPROVED_TRANSLATIONS.md` when useful.
6. Follow the user's requested language pair; otherwise apply repository default routing.

## Source protection

Never modify or overwrite the source file.

## Translation mode

First inspect the document sufficiently to understand:
- document type;
- overall structure;
- major sections;
- speakers if applicable;
- recurring terminology;
- domain concepts and technical notation;
- tone and discourse style.

If the document can be translated reliably as one unit, translate it directly.

If chunking is required, follow the complete chunking protocol in `AGENTS.md`.

Standard source chunks must contain 1,500–1,600 source words.

The final remainder chunk may be shorter than 1,500 words.

Never exceed 1,600 source words for a standard chunk.

Do not ask the user to split the document manually.

Use `scripts/split_source.py` and `scripts/check_chunks.py` when practical so the chunk constraint is checked deterministically.

## Translation requirements

Translate all source content.

Do not:
- summarize;
- omit;
- shorten;
- add subject-matter knowledge;
- explain the source;
- silently correct the author;
- change the author's degree of certainty.

For translation into Vietnamese, produce natural Vietnamese according to the anti-translationese rules in `AGENTS.md`.

For translation into English, produce faithful natural English.

For any other target language, produce idiomatic, accurate prose appropriate to that language while preserving the source's tone and degree of certainty.

## QA

Perform chunk-level QA when chunks are used.

After completing the entire document:
1. assemble all translated content in exact source order;
2. verify completeness;
3. verify terminology consistency;
4. perform final fidelity QA;
5. perform final target-language naturalness QA.

Write only the completed reader-facing translation to `translations/<target-language-code>/`.

Store intermediate chunk files only under `work/`.

Report:
- final output path;
- unresolved terminology;
- genuine source ambiguities;
- QA failures, if any.
