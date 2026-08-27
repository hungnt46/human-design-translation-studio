#!/usr/bin/env python3
"""Remove repeated running header/page-number pairs from extracted PDF Markdown.

The extractor retains the book's printed running head and page number at the
start of many PDF pages.  They are presentation artifacts, not body text, and
split paragraphs in source chunks.  A pair is removed only when it immediately
follows a ``<!-- NNN -->`` PDF marker and the printed number equals ``NNN - 2``
(the offset used by this edition).  The PDF marker itself is retained.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PAGE_MARKER_RE = re.compile(r"^<!--\s*(\d+)\s*-->$")
PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")


def normalize(text: str) -> tuple[str, list[tuple[int, str, int]]]:
    lines = text.splitlines(keepends=True)
    removed: list[tuple[int, str, int]] = []
    index = 0

    while index < len(lines):
        marker = PAGE_MARKER_RE.match(lines[index].strip())
        if not marker:
            index += 1
            continue

        header_index = index + 1
        while header_index < len(lines) and not lines[header_index].strip():
            header_index += 1
        page_number_index = header_index + 1
        while page_number_index < len(lines) and not lines[page_number_index].strip():
            page_number_index += 1

        if (
            header_index < len(lines)
            and page_number_index < len(lines)
            and PAGE_NUMBER_RE.fullmatch(lines[page_number_index].strip())
            and int(lines[page_number_index].strip()) == int(marker.group(1)) - 2
        ):
            header = lines[header_index].strip()
            # Do not treat a bare number or an empty line as a running header.
            if header and not PAGE_NUMBER_RE.fullmatch(header):
                removed.append((int(marker.group(1)), header, int(lines[page_number_index].strip())))
                del lines[header_index : page_number_index + 1]
        index += 1

    return "".join(lines), removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    cleaned, removed = normalize(source.read_text(encoding="utf-8"))

    for pdf_page, header, printed_page in removed:
        print(f"PDF {pdf_page:03d}: {header} [{printed_page}]")
    print(f"Running header/page-number pairs removed: {len(removed)}")

    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(cleaned, encoding="utf-8")


if __name__ == "__main__":
    main()
