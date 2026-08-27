#!/usr/bin/env python3
"""Extract reader-facing Markdown from an EPUB XHTML spine item.

The supplied EPUB contains a small number of invalid UTF-8 bytes.  Reading
with ``surrogateescape`` keeps those bytes visible without corrupting the
otherwise-valid UTF-8 Chinese and typographic characters.
"""

from __future__ import annotations

import argparse
import html
import re
from html.parser import HTMLParser
from pathlib import Path


class Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.current: list[str] | None = None
        self.current_style = ""
        self.current_has_bold = False
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "body":
            self.in_body = True
        elif self.in_body and tag == "p":
            self.current = []
            self.current_style = attributes.get("style", "")
            self.current_has_bold = "font-weight:bold" in self.current_style.lower().replace(" ", "")
        elif self.in_body and tag == "span" and self.current is not None:
            style = attributes.get("style", "").lower().replace(" ", "")
            self.current_has_bold = self.current_has_bold or "font-weight:bold" in style
        elif self.in_body and tag == "br" and self.current is not None:
            self.current.append("\n")
        elif self.in_body and tag == "img" and self.current is not None:
            alt = attributes.get("alt", "image")
            self.current.append(f"[{alt}]")

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self.current is not None:
            text = html.unescape("".join(self.current)).replace("\xa0", " ")
            text = re.sub(r"[ \t\r\n]+", " ", text).strip()
            if text:
                self.blocks.append(self._markdown_block(text, self.current_style, self.current_has_bold))
            self.current = None
            self.current_style = ""
            self.current_has_bold = False
        elif tag == "body":
            self.in_body = False

    def handle_data(self, data: str) -> None:
        if self.in_body and self.current is not None:
            self.current.append(data)

    @staticmethod
    def _markdown_block(text: str, style: str, has_bold: bool) -> str:
        compact_style = style.lower().replace(" ", "")
        bold = has_bold or "font-weight:bold" in compact_style
        size_match = re.search(r"font-size:([0-9.]+)rem", compact_style)
        size = float(size_match.group(1)) if size_match else 0.0
        if bold and size >= 1.5:
            return f"## {text}"
        if bold and size >= 1.3:
            return f"# {text}"
        if bold and size >= 1.0:
            return f"### {text}"
        return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw = args.source.read_bytes()
    text = raw.decode("utf-8", errors="surrogateescape")
    extractor = Extractor()
    extractor.feed(text)
    extractor.close()
    output = "\n\n".join(extractor.blocks) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8", errors="backslashreplace")


if __name__ == "__main__":
    main()
