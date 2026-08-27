from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from split_source import (  # noqa: E402
    build_chunks,
    count_generic,
    is_safe_chunk_transition,
    semantic_units,
    sentence_units,
)


def split_text(text: str) -> list[str]:
    units = semantic_units(text, count_generic, "en")
    units = sentence_units(units, count_generic, "en")
    return build_chunks(units, count_generic)


class ChunkBoundaryTests(unittest.TestCase):
    def assert_valid_chunks(self, source: str, chunks: list[str]) -> None:
        self.assertEqual("".join(chunks), source)
        for current, following in zip(chunks, chunks[1:]):
            self.assertLessEqual(count_generic(current), 1600)
            self.assertTrue(is_safe_chunk_transition(current, following, "en"))

    def test_pdf_hard_wrap_does_not_split_qigong_sentence(self) -> None:
        filler = ("One two three four five six seven eight nine ten.\n\n" * 159)
        sentence = (
            "The content of the basic operation of Qigong includes the main Qigong exercise\n\n"
            "skills and their standardizations.\n\n"
        )
        source = filler + sentence + ("Alpha beta gamma delta epsilon zeta eta theta iota kappa.\n\n" * 159)
        chunks = split_text(source)

        self.assert_valid_chunks(source, chunks)
        self.assertTrue(any(sentence in chunk for chunk in chunks))

    def test_pdf_hard_wrap_does_not_split_footnote(self) -> None:
        filler = ("One two three four five six seven eight nine ten.\n\n" * 159)
        footnote = (
            "i The term “tiao” 调, here translated as “adjust,” may also be translated as "
            "“regulate” or “tune,” as\n\n"
            "in tuning a piano, or as “alignment.”\n\n"
        )
        source = filler + footnote + ("Alpha beta gamma delta epsilon zeta eta theta iota kappa.\n\n" * 159)
        chunks = split_text(source)

        self.assert_valid_chunks(source, chunks)
        self.assertTrue(any(footnote in chunk for chunk in chunks))

    def test_legacy_mid_sentence_transition_is_rejected(self) -> None:
        current = "The content includes the main Qigong exercise\n\n"
        following = "skills and their standardizations."
        self.assertFalse(is_safe_chunk_transition(current, following, "en"))

if __name__ == "__main__":
    unittest.main()
