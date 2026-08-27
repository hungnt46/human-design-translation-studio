# Work Directory

Intermediate files for long-document processing live here.

Recommended structure:

```text
work/<document_id>/
├── manifest.yaml
├── source_chunks/
├── translated_chunks/
└── qa/
```

Do not treat chunk files as the final translation.

The final translation belongs under `translations/` only after assembly and document-level QA.
