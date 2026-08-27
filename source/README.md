# Source Files

Place material to be translated under this directory. Sources may cover any subject and may be books, articles, transcripts, subtitles, documentation, UI text, or other supported document types.

Legacy routes provide defaults:

- `en_to_vi/` defaults to English -> Vietnamese.
- `other_to_en/` defaults to non-English -> English.

You may also create project or inbox subdirectories. When using another route or language pair, specify the source and target languages in the request. Source files are read-only: translations belong under `translations/<target-language-code>/`.
