#!/usr/bin/env python3
"""Machine-translate deterministic source chunks with paragraph fidelity.

This utility keeps chunk boundaries and Markdown structural markers intact. It
uses a Google Translate public endpoint for the requested language pair and
is deliberately resumable: existing translated chunks are never overwritten
unless ``--force`` is provided.

This helper does not replace the editorial and QA workflow in ``AGENTS.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

ENDPOINT = "https://clients5.google.com/translate_a/t"
MAX_CHARS = 4_500
MAX_PARAGRAPHS_PER_BATCH = 1

STRUCTURAL_RE = re.compile(
    r"<!--[^\n]*?-->"
    r"|\b(?:CV|GV|BL|GB|HT|KI|LI|LU|PC|SI|SP|ST|SJ)-?\d+(?:-\d+)?\b"
    r"|\bEX-HN-\d+\b"
)


def load_markdown_glossary(path: Path) -> dict[str, str]:
    """Read APPROVED exact source-to-target mappings from a glossary table."""
    mapping: dict[str, str] = {}
    row_re = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*APPROVED\s*\|",
        flags=re.IGNORECASE,
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        match = row_re.match(line)
        if not match:
            continue
        source, target = (value.strip() for value in match.groups())
        mapping[source] = target
        # Glossary abbreviations describe the first-use rendering but the book
        # commonly prints the unabbreviated term on its own as well.
        mapping.setdefault(re.sub(r"\s+\([A-Z0-9]+\)$", "", source), target)
        if " / " in source:
            for alternative in source.split(" / "):
                mapping.setdefault(alternative.strip(), target)
    return mapping

def protect_terms(
    text: str,
    terms: list[str],
    term_map: dict[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    mapped_terms = term_map or {}
    all_terms = set(terms) | set(mapped_terms)
    for number, term in enumerate(sorted(all_terms, key=len, reverse=True)):
        token = f"XQAA{number:03d}QX"
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)")
        text, count = pattern.subn(token, text)
        if count:
            replacements[token] = mapped_terms.get(term, term)
    return text, replacements


def apply_terms_direct(text: str, term_map: dict[str, str]) -> str:
    """Seed approved Vietnamese terms while leaving sentence context visible."""
    for source, target in sorted(term_map.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", flags=re.IGNORECASE)
        text = pattern.sub(lambda _match, value=target: value, text)
    return text


def canonicalize_targets(text: str, term_map: dict[str, str]) -> str:
    """Restore exact approved casing after mixed-language translation."""
    for target in sorted(set(term_map.values()), key=len, reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(target)}(?!\w)", flags=re.IGNORECASE)
        text = pattern.sub(lambda _match, value=target: value, text)
    return text


def protect_structural_text(
    text: str, replacements: dict[str, str]
) -> tuple[str, dict[str, str]]:
    """Protect page markers and source medical codes from translation."""
    counter = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal counter
        token = f"XQZZ{counter:04d}QX"
        counter += 1
        replacements[token] = match.group(0)
        return token

    return STRUCTURAL_RE.sub(replace, text), replacements


def split_for_request(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > MAX_CHARS:
        window = remaining[: MAX_CHARS + 1]
        cuts = [m.end() for m in re.finditer(r"(?<=[.!?…])\s+", window)]
        cut = cuts[-1] if cuts else max(window.rfind(" "), window.rfind("\n"))
        if cut <= 0:
            raise RuntimeError("No safe sentence or word boundary found in an oversized paragraph.")
        parts.append(remaining[:cut])
        remaining = remaining[cut:]
    parts.append(remaining)
    return parts


def translate_request(text: str, source_language: str, target_language: str) -> str:
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = subprocess.run(
                [
                    "curl", "-sS", "--fail", "--max-time", "25", "--get", ENDPOINT,
                    "--data-urlencode", "client=dict-chrome-ex",
                    "--data-urlencode", f"sl={source_language}",
                    "--data-urlencode", f"tl={target_language}",
                    "--data-urlencode", "dt=t",
                    "--data-urlencode", f"q={text}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(response.stdout)
            if isinstance(payload, list) and payload and isinstance(payload[0], str):
                return "".join(payload)
            return "".join(piece[0] for piece in payload[0] if piece and piece[0] is not None)
        except Exception as error:  # network service failures are retried deterministically
            last_error = error
            time.sleep(2**attempt)
    raise RuntimeError(f"Translation request failed after retries: {last_error}")


def translate_block(block: str, source_language: str, target_language: str) -> str:
    marker = re.match(r"^(#{1,6}[ \t]+)(.*)$", block, flags=re.DOTALL)
    prefix, content = (marker.group(1), marker.group(2)) if marker else ("", block)
    translated = "".join(
        translate_request(part, source_language, target_language)
        for part in split_for_request(content)
    )
    return prefix + translated


def translate_chunk(
    source: Path,
    target: Path,
    source_language: str,
    target_language: str,
    protected_terms: list[str],
    term_map: dict[str, str],
    direct_terms: bool,
) -> None:
    text = source.read_text(encoding="utf-8")
    if direct_terms:
        text, replacements = protect_terms(text, protected_terms)
        text = apply_terms_direct(text, term_map)
    else:
        text, replacements = protect_terms(text, protected_terms, term_map)
    text, replacements = protect_structural_text(text, replacements)
    paragraphs = [part for part in re.split(r"\n[ \t]*\n+", text) if part]
    batches: list[tuple[str, list[str]]] = []
    current: list[str] = []
    current_size = 0
    batch_number = 0
    for paragraph in paragraphs:
        # Each marker is unique.  We verify it after translation rather than
        # assuming that a remote service preserved structural separators.
        marker_size = 16
        # Keep batches small: long contextual batches can silently degrade
        # fidelity in the unauthenticated endpoint, while three paragraphs
        # retain useful local context and remain readily verifiable.
        if current and (
            current_size + len(paragraph) + marker_size > MAX_CHARS
            or len(current) >= MAX_PARAGRAPHS_PER_BATCH
        ):
            batches.append((f"XQBR{batch_number:06d}QX", current))
            batch_number += 1
            current, current_size = [], 0
        current.append(paragraph)
        current_size += len(paragraph) + marker_size
    if current:
        batches.append((f"XQBR{batch_number:06d}QX", current))

    rendered_batches: list[str] = []
    for batch_marker, batch in batches:
        markers = [f"{batch_marker}{index:04d}XQ" for index in range(len(batch) - 1)]
        request_text = "".join(
            paragraph + (f" {markers[index]} " if index < len(markers) else "")
            for index, paragraph in enumerate(batch)
        )
        response = "".join(
            translate_request(part, source_language, target_language)
            for part in split_for_request(request_text)
        )
        if all(marker in response for marker in markers):
            for marker in markers:
                response = re.sub(rf"\s*{re.escape(marker)}\s*", "\n\n", response)
        else:
            # A rare endpoint normalization must not collapse source structure.
            response = "\n\n".join(
                translate_block(paragraph, source_language, target_language)
                for paragraph in batch
            )
        rendered_batches.append(response)

    translated = "\n\n".join(rendered_batches)
    for token, term in replacements.items():
        translated = translated.replace(token, term)
    if direct_terms:
        translated = canonicalize_targets(translated, term_map)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(translated, encoding="utf-8")


def update_manifest(manifest_path: Path, completed: set[str]) -> None:
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for entry in data["chunks"]:
        if entry["id"] in completed:
            entry["translation_status"] = "completed"
            entry["qa_status"] = "machine-translated; pending editorial QA"
    manifest_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--source-language",
        help="Override the manifest source language code; use 'auto' for detection.",
    )
    parser.add_argument(
        "--target-language",
        help="Override the manifest target language code.",
    )
    parser.add_argument(
        "--protect-term",
        action="append",
        default=[],
        help="Exact source term to preserve; repeat this option for multiple terms.",
    )
    parser.add_argument(
        "--term-map",
        type=Path,
        help="UTF-8 JSON object mapping exact source terms to required target renderings.",
    )
    parser.add_argument(
        "--term-glossary",
        type=Path,
        action="append",
        default=[],
        help="Markdown glossary whose APPROVED table rows must be applied exactly.",
    )
    parser.add_argument(
        "--direct-terms",
        action="store_true",
        help="Seed approved target terms directly so sentence context remains visible.",
    )
    parser.add_argument(
        "--no-manifest-update",
        action="store_true",
        help="Leave manifest statuses untouched (useful for parallel ranges).",
    )
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    source_language = args.source_language or data.get("source_language") or "auto"
    if source_language in {"auto-whitespace", "unknown"}:
        source_language = "auto"
    target_language = args.target_language or data.get("target_language")
    if not target_language:
        raise SystemExit("Target language is required in the manifest or --target-language.")
    term_map: dict[str, str] = {}
    if args.term_map:
        raw_map = json.loads(args.term_map.read_text(encoding="utf-8"))
        if not isinstance(raw_map, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in raw_map.items()
        ):
            raise SystemExit("--term-map must contain a JSON object of string-to-string entries.")
        term_map = raw_map
    for glossary_path in args.term_glossary:
        term_map.update(load_markdown_glossary(glossary_path))
    end = args.end or len(data["chunks"])
    completed: set[str] = set()
    for index, entry in enumerate(data["chunks"], start=1):
        if not args.start <= index <= end:
            continue
        source = Path(entry["source_path"])
        target = manifest.parent / "translated_chunks" / f"{entry['id']}.md"
        if target.exists() and not args.force:
            print(f"SKIP {entry['id']}", flush=True)
            completed.add(entry["id"])
            continue
        print(f"TRANSLATING {entry['id']}", flush=True)
        translate_chunk(
            source,
            target,
            source_language,
            target_language,
            args.protect_term,
            term_map,
            args.direct_terms,
        )
        completed.add(entry["id"])
        print(f"COMPLETED {entry['id']}", flush=True)
        time.sleep(0.2)
    if not args.no_manifest_update:
        update_manifest(manifest, completed)


if __name__ == "__main__":
    main()
