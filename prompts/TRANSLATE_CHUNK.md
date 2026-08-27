# Translate One Chunk

Translate the requested source chunk according to `AGENTS.md`.

Before translating:

1. read the general glossary;
2. read only relevant domain glossaries;
3. consult relevant terminology decisions;
4. consult relevant approved translations;
5. inspect the document manifest;
6. inspect the previous translated chunk when necessary for continuity.

Previous chunks are context only.

Do not reproduce text from previous chunks.

Preserve:
- all source meaning;
- terminology;
- speaker voice;
- examples;
- conditions;
- exceptions;
- modality;
- rhetorical emphasis;
- conceptual continuity.

For translation into Vietnamese:

Use semantic fidelity with syntactic freedom.

The output must read like natural Vietnamese rather than prose mechanically copied from source-language syntax.

For any other target language, apply the equivalent native-language naturalness standard.

Do not summarize or simplify.

After translation, perform the chunk-level fidelity and natural-language QA defined in `AGENTS.md`.

Write the translated chunk to:

`work/<document_id>/translated_chunks/<same_chunk_name>`

Update the manifest status.

Do not modify the source chunk.
