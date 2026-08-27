#!/usr/bin/env python3
"""
Validate chunk sizes, source integrity, and semantic boundaries from a manifest.yaml.

Validation fails when a non-final chunk appears to end mid-sentence or when the
next chunk clearly begins as a continuation. A non-final chunk below 1500 words
is reported as a warning because semantic integrity takes priority over padding
or cutting an idea to reach the target minimum.

Usage:
  python scripts/check_chunks.py work/<document_id>/manifest.yaml
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path
import yaml

from split_source import is_safe_chunk_transition

MIN_WORDS = 1500
MAX_WORDS = 1600
WORD_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)

def count_generic(text: str) -> int:
    return len(WORD_RE.findall(text))

def count_zh(text: str) -> int:
    import jieba
    return len([t for t in jieba.cut(text) if t.strip() and not re.fullmatch(r"\W+", t)])

def count_ja(text: str) -> int:
    from janome.tokenizer import Tokenizer
    tokenizer = Tokenizer()
    count = 0
    for token in tokenizer.tokenize(text):
        surface = token.surface.strip()
        if surface and not re.fullmatch(r"[\W_]+", surface, re.UNICODE):
            count += 1
    return count

def counter_for(lang: str):
    lang = (lang or "").lower()
    if lang.startswith("zh"):
        return count_zh
    if lang.startswith("ja"):
        return count_ja
    return count_generic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    source_path = Path(data["source_file"])
    if not source_path.is_absolute():
        source_path = (manifest_path.parent / source_path).resolve()

    source_text = source_path.read_text(encoding="utf-8")
    counter = counter_for(data.get("source_language", ""))

    chunks = []
    errors = []
    warnings = []
    chunk_entries = data.get("chunks", [])

    for idx, entry in enumerate(chunk_entries):
        p = Path(entry["source_path"])
        if not p.is_absolute():
            # First try relative to current working directory, then manifest directory.
            if not p.exists():
                p = (manifest_path.parent / p).resolve()
        if not p.exists():
            errors.append(f"Missing chunk file: {entry['source_path']}")
            continue
        text = p.read_text(encoding="utf-8")
        chunks.append(text)
        wc = counter(text)
        is_final = idx == len(chunk_entries) - 1
        if wc > MAX_WORDS:
            errors.append(f"{entry['id']} exceeds {MAX_WORDS}: {wc}")
        if not is_final and wc < MIN_WORDS:
            warnings.append(
                f"{entry['id']} is below {MIN_WORDS}: {wc}. "
                "This is acceptable only when no later verified boundary fits below the hard maximum."
            )
        if wc != entry.get("source_words"):
            errors.append(
                f"{entry['id']} manifest word count={entry.get('source_words')} but actual={wc}"
            )

    reconstructed = "".join(chunks)
    if reconstructed != source_text:
        errors.append("Concatenated chunks do not exactly reproduce the source.")

    total = counter(source_text)
    if total != data.get("total_source_words"):
        errors.append(
            f"Manifest total_source_words={data.get('total_source_words')} but actual={total}"
        )

    for idx in range(len(chunks) - 1):
        if not is_safe_chunk_transition(
            chunks[idx], chunks[idx + 1], data.get("source_language", "")
        ):
            end_preview = " ".join(chunks[idx].rstrip().split())[-100:]
            start_preview = " ".join(chunks[idx + 1].lstrip().split())[:100]
            errors.append(
                f"{chunk_entries[idx]['id']} -> {chunk_entries[idx + 1]['id']} is an "
                f"unsafe transition (likely mid-sentence/idea): ...{end_preview} | {start_preview}..."
            )

    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print("VALIDATION PASSED")
    for warning in warnings:
        print(f"WARNING: {warning}")
    print(f"Source word units: {total}")
    print(f"Chunk count: {len(chunks)}")
    for idx, text in enumerate(chunks, start=1):
        print(f"  chunk_{idx:03d}: {counter(text)}")

if __name__ == "__main__":
    main()
