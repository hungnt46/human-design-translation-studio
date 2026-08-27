#!/usr/bin/env python3
"""
Split a long source into deterministic chunks for the General Translation Studio.

Policy:
- standard chunks: 1500-1600 SOURCE word units
- hard max: 1600
- final remainder may be shorter
- no overlap
- every non-final chunk must end at a verified sentence or structural boundary
- prefer section/paragraph boundaries, then sentence boundaries
- do not treat PDF hard-wrapped lines as paragraph boundaries
- preserve source text exactly across chunk concatenation

Word counting:
- English / whitespace-delimited languages: Unicode word regex
- Chinese: jieba tokenizer
- Japanese: Janome tokenizer

Usage:
  python scripts/split_source.py source/en_to_vi/file.md \
      --document-id my_doc \
      --source-language en \
      --target-language vi
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import Callable, List, Tuple
import yaml

MIN_WORDS = 1500
MAX_WORDS = 1600

WORD_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)

COMMON_ABBREVIATIONS = {
    "adj", "approx", "assn", "bros", "cf", "ch", "dept", "dr", "e.g",
    "ed", "eds", "eq", "esp", "etc", "fig", "figs", "i.e", "inc", "jr",
    "lat", "mr", "mrs", "ms", "mt", "no", "nos", "p", "pp", "prof",
    "rev", "sec", "sr", "st", "trans", "univ", "vol", "vols", "vs",
}

TERMINAL_RE = re.compile(
    r"(?P<terminal>[.!?…。！？]+)"
    r"(?P<closers>[\"'’”»）)\]\}*_`~]*)"
    r"(?P<citation>(?:\s*\[[^\]\n]{1,40}\])?)$"
)

def count_generic(text: str) -> int:
    return len(WORD_RE.findall(text))

def count_zh(text: str) -> int:
    try:
        import jieba
    except ImportError as e:
        raise SystemExit("Chinese counting requires `pip install -r requirements.txt`.") from e
    tokens = [t for t in jieba.cut(text) if t.strip() and not re.fullmatch(r"\W+", t)]
    return len(tokens)

def count_ja(text: str) -> int:
    try:
        from janome.tokenizer import Tokenizer
    except ImportError as e:
        raise SystemExit("Japanese counting requires `pip install -r requirements.txt`.") from e
    tokenizer = Tokenizer()
    count = 0
    for token in tokenizer.tokenize(text):
        surface = token.surface.strip()
        if not surface:
            continue
        # Ignore pure punctuation/symbols.
        if re.fullmatch(r"[\W_]+", surface, re.UNICODE):
            continue
        count += 1
    return count

def language_counter(language: str) -> Callable[[str], int]:
    lang = language.lower()
    if lang.startswith("zh"):
        return count_zh
    if lang.startswith("ja"):
        return count_ja
    return count_generic

def infer_language(text: str) -> str:
    sample = text[:20000]
    hira_kata = len(re.findall(r"[\u3040-\u30ff]", sample))
    han = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", sample))
    latin = len(re.findall(r"[A-Za-z]", sample))
    if hira_kata > 50:
        return "ja"
    if han > 100 and latin < han:
        return "zh"
    return "auto-whitespace"

def paragraph_units(text: str) -> List[Tuple[str, bool]]:
    """
    Return exact-text units. Each unit is (text, paragraph_end).
    Blank-line separators are attached to the preceding paragraph so
    concatenating all units reproduces the original source exactly.
    """
    if not text:
        return []
    parts = re.split(r"(\n[ \t]*\n+)", text)
    units: List[Tuple[str, bool]] = []
    i = 0
    while i < len(parts):
        body = parts[i]
        sep = ""
        if i + 1 < len(parts) and re.fullmatch(r"\n[ \t]*\n+", parts[i + 1] or ""):
            sep = parts[i + 1]
            i += 2
        else:
            i += 1
        if body or sep:
            units.append((body + sep, True))
    return units


def _content_without_trailing_space(text: str) -> str:
    return text.rstrip()


def _period_is_abbreviation(text_before_terminal: str) -> bool:
    """Conservatively reject periods that are likely abbreviations or initials."""
    token_match = re.search(r"([A-Za-z][A-Za-z.]*)$", text_before_terminal)
    if not token_match:
        return False
    token = token_match.group(1)
    normalized = token.lower().rstrip(".")
    if normalized in COMMON_ABBREVIATIONS:
        return True
    if len(token) == 1 and token.isalpha():
        return True
    if re.fullmatch(r"(?:[A-Za-z]{1,4}\.)+[A-Za-z]{1,4}", token):
        return True
    return False


def has_terminal_ending(text: str, language: str = "") -> bool:
    """Return True when text ends at a credible sentence boundary."""
    stripped = _content_without_trailing_space(text)
    match = TERMINAL_RE.search(stripped)
    if not match:
        return False
    terminal = match.group("terminal")
    if terminal == "." and _period_is_abbreviation(stripped[: match.start("terminal")]):
        return False
    return True


def is_structural_block(text: str) -> bool:
    """Recognize conservative standalone structures that express a complete idea."""
    stripped = text.strip()
    if not stripped:
        return False
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    flattened = " ".join(lines)
    if re.search(r"\.{3,}", flattened) and re.search(r"\d+\s*$", flattened):
        return True
    if "(" in flattened and flattened.endswith(")"):
        return True
    if re.search(r"[A-Za-zÀ-ỹ]", flattened) and re.search(
        r"\b\d+(?:[–-]\d+)?(?:\s*[,;]\s*\d+(?:[–-]\d+)?)*\s*$",
        flattened,
    ):
        return True
    if len(lines) != 1:
        return False
    line = lines[0]
    if re.fullmatch(r"<!--.*?-->", line):
        return True
    if re.match(r"^#{1,6}\s+\S", line):
        return True
    if re.match(r"^```|^~~~", line):
        return True
    if line.startswith("|") and line.endswith("|"):
        return True
    if re.fullmatch(r"[-*_]{3,}", line):
        return True
    if re.match(r"^(?:[A-Z]|[IVXLCDM]+|\d+)[.)]\s+\S", line):
        return True
    return False


def begins_obvious_continuation(text: str) -> bool:
    """Detect a next block that clearly continues the preceding line or idea."""
    stripped = text.lstrip()
    if not stripped:
        return False
    first_line = stripped.splitlines()[0].strip()
    if not first_line:
        return False
    if first_line[0].islower():
        return True
    if first_line.startswith(("(", ")", "]", "}", ",", ";", ":", "–", "—")):
        return True
    if re.fullmatch(r"\d+(?:[–-]\d+)?(?:\s*[,;]\s*\d+(?:[–-]\d+)?)*[.,]?", first_line):
        return True
    return False


def is_safe_boundary_text(text: str, language: str = "") -> bool:
    """Check whether the end of text is safe for a non-final chunk boundary."""
    if has_terminal_ending(text, language):
        return True
    parts = re.split(r"\n[ \t]*\n+", text.rstrip())
    for width in range(1, min(4, len(parts)) + 1):
        if is_structural_block("\n\n".join(parts[-width:])):
            return True
    if len(parts) >= 2 and re.fullmatch(r"\d+", parts[-1].strip()):
        return bool(re.fullmatch(r"<!--\s*PDF page \d+\s*-->", parts[-2].strip()))
    return False


def is_safe_chunk_transition(current: str, following: str, language: str = "") -> bool:
    """Validate both the chunk ending and the beginning of the next chunk."""
    return is_safe_boundary_text(current, language) and not begins_obvious_continuation(following)


def semantic_units(
    text: str,
    counter: Callable[[str], int],
    language: str,
) -> List[Tuple[str, bool]]:
    """
    Coalesce raw blank-line blocks until a safe semantic boundary is reached.

    PDF extraction often inserts a blank line after every visually wrapped line.
    Those separators are retained exactly but are not considered boundaries unless
    the accumulated text ends a sentence or a conservative standalone structure.
    """
    raw_units = paragraph_units(text)
    result: List[Tuple[str, bool]] = []
    pending: List[str] = []

    for index, (raw_text, _) in enumerate(raw_units):
        pending.append(raw_text)
        combined = "".join(pending)
        structural = is_structural_block(combined)
        following = raw_units[index + 1][0] if index + 1 < len(raw_units) else ""
        safe_end = has_terminal_ending(combined, language) or structural
        if safe_end and not begins_obvious_continuation(following):
            result.append((combined, True))
            pending = []
            continue
        if counter(combined) > MAX_WORDS:
            sentence_parts = split_sentences_exact(combined, language)
            safe_parts: List[str] = []
            remainder = ""
            for part in sentence_parts:
                if not remainder and has_terminal_ending(part, language):
                    safe_parts.append(part)
                else:
                    remainder += part
            if not safe_parts:
                raise SystemExit(
                    "A semantic unit exceeds 1600 word units without a verified sentence "
                    "or structural boundary. Review extraction/formatting; the script will "
                    "not split at a PDF line wrap or in the middle of a sentence."
                )
            for part in safe_parts:
                if counter(part) > MAX_WORDS:
                    raise SystemExit(
                        "A single sentence exceeds 1600 word units. Review the source "
                        "manually; the script will not split inside the sentence."
                    )
                result.append((part, False))
            pending = [remainder] if remainder else []

    if pending:
        # The physical end of the source is always a valid final boundary. It may
        # contain an intentionally fragmentary title, caption, or source defect.
        result.append(("".join(pending), True))

    return result

def split_sentences_exact(text: str, language: str) -> List[str]:
    """
    Split a paragraph into sentence-like exact slices.
    Concatenation always reproduces the original paragraph.
    """
    if not text:
        return []

    pattern = re.compile(r"[.!?…。！？]+[\"'’”»）)\]\}*_`~]*(?:\s*\[[^\]\n]{1,40}\])?(?=\s|$)")
    cuts: List[int] = []
    for match in pattern.finditer(text):
        prefix = text[: match.end()]
        following = text[match.end():]
        if has_terminal_ending(prefix, language) and not begins_obvious_continuation(following):
            cuts.append(match.end())
    if not cuts:
        return [text]
    pieces: List[str] = []
    start = 0
    for cut in cuts:
        pieces.append(text[start:cut])
        start = cut
    if start < len(text):
        remainder = text[start:]
        if not remainder.strip() and pieces:
            # Keep separators with the completed sentence. This makes a chunk
            # boundary visually clean instead of starting the next file blank.
            pieces[-1] += remainder
        else:
            pieces.append(remainder)
    return [piece for piece in pieces if piece]

def sentence_units(
    units: List[Tuple[str, bool]],
    counter: Callable[[str], int],
    language: str,
) -> List[Tuple[str, bool]]:
    """Convert semantic blocks to sentence-granular, exact-text units."""
    result: List[Tuple[str, bool]] = []
    for text, paragraph_end in units:
        sentences = split_sentences_exact(text, language)
        if len(sentences) <= 1:
            if counter(text) > MAX_WORDS:
                raise SystemExit(
                    "A semantic unit exceeds 1600 word units but has no safe sentence "
                    "boundary. Review the source manually; the script will not split "
                    "mid-sentence."
                )
            result.append((text, paragraph_end))
            continue
        for idx, sent in enumerate(sentences):
            if counter(sent) > MAX_WORDS:
                raise SystemExit(
                    "A single sentence exceeds 1600 word units. "
                    "Review the source manually; the script will not split inside a sentence."
                )
            result.append((sent, paragraph_end and idx == len(sentences) - 1))
    return result


def build_chunks(
    units: List[Tuple[str, bool]],
    counter: Callable[[str], int],
) -> List[str]:
    chunks: List[str] = []
    current: List[Tuple[str, bool]] = []

    def text_of(items):
        return "".join(x[0] for x in items)

    for unit in units:
        candidate = current + [unit]
        candidate_count = counter(text_of(candidate))

        if candidate_count <= MAX_WORDS:
            current = candidate
            continue

        if not current:
            raise SystemExit("Internal error: one unit exceeds the hard maximum.")

        current_count = counter(text_of(current))

        # Prefer a paragraph boundary within the target range.
        best_cut = None
        running = ""
        for idx, (u_text, p_end) in enumerate(current, start=1):
            running += u_text
            c = counter(running)
            if MIN_WORDS <= c <= MAX_WORDS and p_end:
                best_cut = idx

        if best_cut is not None:
            head = current[:best_cut]
            tail = current[best_cut:]
            chunks.append(text_of(head))
            current = tail + [unit]
        else:
            # No paragraph boundary in range. Cut at the latest safe sentence/unit boundary
            # not exceeding the hard maximum.
            chunks.append(text_of(current))
            current = [unit]

    if current:
        chunks.append(text_of(current))

    # Rebalance only when the penultimate chunk is below MIN due to sentence boundaries
    # and merging would not exceed MAX. Never alter text.
    if len(chunks) >= 2:
        prev_count = counter(chunks[-2])
        last_count = counter(chunks[-1])
        if prev_count < MIN_WORDS and prev_count + last_count <= MAX_WORDS:
            chunks[-2] = chunks[-2] + chunks[-1]
            chunks.pop()

    return chunks

def write_manifest(
    manifest_path: Path,
    source_file: Path,
    source_language: str,
    target_language: str,
    chunks: List[str],
    counter: Callable[[str], int],
):
    data = {
        "document_id": manifest_path.parent.name,
        "source_file": str(source_file),
        "source_language": source_language,
        "target_language": target_language,
        "total_source_words": counter(source_file.read_text(encoding="utf-8")),
        "chunk_policy": {
            "standard_min_words": MIN_WORDS,
            "standard_max_words": MAX_WORDS,
            "final_chunk_may_be_shorter": True,
            "verified_sentence_or_structure_boundary_required": True,
            "pdf_hard_wrap_is_not_a_boundary": True,
            "nonfinal_chunk_may_be_shorter_when_no_safe_boundary_fits": True,
            "overlap": 0,
        },
        "total_chunk_count": len(chunks),
        "chunks": [],
    }
    for i, chunk in enumerate(chunks, start=1):
        data["chunks"].append(
            {
                "id": f"chunk_{i:03d}",
                "source_path": str(manifest_path.parent / "source_chunks" / f"chunk_{i:03d}.md"),
                "source_words": counter(chunk),
                "translation_status": "pending",
                "qa_status": "pending",
            }
        )
    manifest_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_file", type=Path)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--source-language", default="auto")
    parser.add_argument(
        "--target-language",
        required=True,
        help="Target language code, for example vi, en, ja, de, or pt-BR.",
    )
    parser.add_argument("--out-root", type=Path, default=Path("work"))
    args = parser.parse_args()

    source_file = args.source_file.resolve()
    text = source_file.read_text(encoding="utf-8")

    language = args.source_language
    if language == "auto":
        language = infer_language(text)

    counter = language_counter(language)
    total_words = counter(text)

    work_dir = args.out_root / args.document_id
    chunks_dir = work_dir / "source_chunks"
    translated_dir = work_dir / "translated_chunks"
    qa_dir = work_dir / "qa"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    translated_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    if total_words <= MAX_WORDS:
        chunks = [text]
    else:
        units = semantic_units(text, counter, language)
        units = sentence_units(units, counter, language)
        chunks = build_chunks(units, counter)

    reconstructed = "".join(chunks)
    if reconstructed != text:
        raise SystemExit("Integrity failure: chunk concatenation does not exactly reproduce source.")

    # Hard validation.
    for i, chunk in enumerate(chunks):
        wc = counter(chunk)
        is_final = i == len(chunks) - 1
        if wc > MAX_WORDS:
            raise SystemExit(f"chunk_{i+1:03d} exceeds {MAX_WORDS}: {wc}")
        if not is_final and wc < MIN_WORDS:
            print(
                f"WARNING: chunk_{i+1:03d} has {wc} word units (< {MIN_WORDS}) "
                "because no later verified sentence/structure boundary fit under the hard maximum."
            )
        following = chunks[i + 1] if not is_final else ""
        if not is_final and not is_safe_chunk_transition(chunk, following, language):
            raise SystemExit(
                f"chunk_{i+1:03d} does not end at a verified sentence or structural boundary."
            )

    for old in chunks_dir.glob("chunk_*.md"):
        old.unlink()
    for i, chunk in enumerate(chunks, start=1):
        (chunks_dir / f"chunk_{i:03d}.md").write_text(chunk, encoding="utf-8")

    manifest_path = work_dir / "manifest.yaml"
    write_manifest(
        manifest_path,
        source_file,
        language,
        args.target_language,
        chunks,
        counter,
    )

    print(f"Source: {source_file}")
    print(f"Detected/selected language: {language}")
    print(f"Total source word units: {total_words}")
    print(f"Chunks created: {len(chunks)}")
    for i, chunk in enumerate(chunks, start=1):
        print(f"  chunk_{i:03d}: {counter(chunk)}")
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    main()
