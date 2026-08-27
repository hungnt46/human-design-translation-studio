# General Translation Studio

A controlled, general-purpose workspace for translating any subject, genre, or document type while preserving source meaning, structure, terminology, and voice.

Human Design remains supported as one optional domain. Its existing sources, translations, work files, and glossary are preserved, but they no longer control unrelated translation projects.

## Language routing

The language pair explicitly requested by the user always takes precedence. When no target language is specified, the repository uses these convenient defaults:

- English -> Vietnamese
- Any non-English language -> English

Any other language pair is supported when named in the request. Output goes to `translations/<target-language-code>/`.

## What can be translated

The workspace is not limited to books or Human Design. It can handle, for example:

- books, articles, essays, and reports;
- lectures, interviews, transcripts, and subtitles;
- marketing, business, academic, medical, legal, and technical material;
- UI copy, documentation, emails, and ordinary text;
- multilingual documents and domain-specific terminology.

The agent must preserve the original format when the available workflow supports it safely. Plain text may be delivered as Markdown.

## Core rules

1. Preserve the complete source meaning and meaningful structure.
2. Never summarize, expand, explain, or fact-check unless explicitly asked.
3. Apply only the glossaries relevant to the current subject and language pair.
4. Produce natural target-language prose rather than literal translationese.
5. Never overwrite source files.
6. Chunk long documents deterministically when needed.
7. Assemble and QA the complete document before considering it finished.

## Repository map

```text
translation-studio/
├── AGENTS.md                    # authoritative translation rules
├── GEMINI.md                    # bootstrap pointing to AGENTS.md
├── glossary/
│   ├── GLOSSARY.md              # cross-domain terms
│   ├── HD_GLOSSARY.md           # optional Human Design terms only
│   └── TERM_DECISIONS.md        # unresolved terms and decision history
├── reference/
│   └── APPROVED_TRANSLATIONS.md
├── prompts/
├── scripts/
├── source/
│   ├── en_to_vi/                # legacy/default route
│   └── other_to_en/             # legacy/default route
├── work/                        # manifests and intermediate chunks
├── translations/
│   └── <target-language-code>/
├── qa/
└── archive/
```

The physical folder can retain its old name without affecting behavior. You may rename it to `translation-studio` later if desired.

## First-time setup

Helper-script dependencies are optional:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Daily workflow

Put a source file anywhere under `source/`. Existing routes remain convenient:

```text
source/en_to_vi/       # defaults to Vietnamese
source/other_to_en/    # defaults to English
```

Then ask, for example:

```text
Translate source/en_to_vi/article.md according to AGENTS.md and
prompts/TRANSLATE_FILE.md. Process the complete file and do not overwrite it.
```

For another language pair, specify the target explicitly:

```text
Translate source/inbox/product-guide.md from English to Japanese according to
AGENTS.md and prompts/TRANSLATE_FILE.md.
```

Expected output:

```text
translations/ja/product-guide.md
```

## Terminology

`glossary/GLOSSARY.md` contains repository-wide approved terms. Put terminology that applies only to one field in a separate domain glossary named `<DOMAIN>_GLOSSARY.md`.

Examples:

- `HD_GLOSSARY.md` for Human Design;
- `MEDICAL_GLOSSARY.md` for a medical project;
- `SOFTWARE_GLOSSARY.md` for software documentation.

Only a relevant domain glossary should be used for a project. When a term is unresolved:

1. flag it for review;
2. record it in `glossary/TERM_DECISIONS.md`;
3. approve it manually;
4. copy the approved decision into the general or appropriate domain glossary.

## Approved translations

Use `reference/APPROVED_TRANSLATIONS.md` for manually approved source-to-translation examples. Examples may be grouped by language pair, subject, genre, or style.

## Long documents

When chunking is needed:

- standard chunk: 1,500–1,600 source words;
- hard maximum: 1,600 source words;
- final remainder may be shorter;
- no overlap, padding, omission, duplication, or mid-sentence split.
- PDF/OCR line wraps and blank lines are not automatically treated as paragraph boundaries;
- when no safe ending fits the target range, a shorter chunk is preferred over a broken sentence or idea.

Example:

```bash
python scripts/split_source.py source/inbox/article.md \
  --document-id article \
  --source-language en \
  --target-language ja

python scripts/check_chunks.py work/article/manifest.yaml
```

## Revision and QA

- Use `prompts/REVISE_VIETNAMESE.md` to improve Vietnamese naturalness without meaning drift.
- Use `prompts/QA_TRANSLATION.md` for a source-to-translation audit.
- Use `prompts/REVIEW_NEW_TERMS.md` to review unresolved terminology in any domain.
- Keep intermediate chunk files under `work/`; do not delete them automatically.

`AGENTS.md` is authoritative for Codex and other compatible agents. `GEMINI.md` points Gemini/Antigravity to the same rules so the two instruction sets do not drift.
