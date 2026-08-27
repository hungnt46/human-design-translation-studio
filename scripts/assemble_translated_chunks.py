#!/usr/bin/env python3
"""Assemble translated chunk files and perform mechanical delivery checks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    translated_dir = manifest_path.parent / "translated_chunks"
    source_chunks: list[str] = []
    translated_chunks: list[str] = []
    missing: list[str] = []

    for entry in data["chunks"]:
        chunk_id = entry["id"]
        source = Path(entry["source_path"])
        target = translated_dir / f"{chunk_id}.md"
        source_chunks.append(source.read_text(encoding="utf-8"))
        if not target.exists() or not target.read_text(encoding="utf-8").strip():
            missing.append(chunk_id)
            continue
        translated_chunks.append(target.read_text(encoding="utf-8"))

    if missing:
        raise SystemExit(f"Missing or empty translated chunks: {', '.join(missing)}")

    source_file = Path(data["source_file"])
    if "".join(source_chunks) != source_file.read_text(encoding="utf-8"):
        raise SystemExit("Source chunks do not reconstruct the extracted source exactly.")

    assembled = "".join(translated_chunks)
    if "ZZTERMPRESERVE" in assembled or re.search(r"XQ(?:AA|BR)\d+", assembled):
        raise SystemExit("Unrestored protected-term placeholder found in assembled translation.")
    source_heading_count = len(re.findall(r"^#{1,6} ", source_file.read_text(encoding="utf-8"), flags=re.MULTILINE))
    target_heading_count = len(re.findall(r"^#{1,6} ", assembled, flags=re.MULTILINE))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(assembled, encoding="utf-8")
    print("ASSEMBLY PASSED")
    print(f"Chunks assembled: {len(translated_chunks)}")
    source_word_count = len(re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*", "".join(source_chunks)))
    print(f"Source words: {source_word_count}")
    print(f"Target characters: {len(assembled)}")
    print(f"Markdown headings (source/target): {source_heading_count}/{target_heading_count}")


if __name__ == "__main__":
    main()
