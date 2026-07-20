"""Document normalization (Phase 2, step 1 of the build guide).

Loaders for Markdown, HTML, plain text, and PDF sources that all normalize
into the same shape: raw text (as read from the source) and cleaned text
(whitespace-normalized, with headings preserved as Markdown `#` lines and,
for PDFs, page numbers preserved as synthetic `## Page N` headings). Keeping
both versions lets you debug indexing issues by diffing raw vs. cleaned.

The cleaned text is intentionally shaped like Markdown so the existing
heading-based chunker (`app.ingestion.chunker.chunk_markdown`) works
uniformly across all four source formats.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

from app.core.models import DocFormat, NormalizedDocument

_HEADING_TAGS = {f"h{i}": i for i in range(1, 7)}
_BLOCK_TAGS = {"p", "div", "li", "br", "tr", "section", "article"}

SUPPORTED_EXTENSIONS: dict[str, DocFormat] = {
    ".md": DocFormat.markdown,
    ".markdown": DocFormat.markdown,
    ".html": DocFormat.html,
    ".htm": DocFormat.html,
    ".txt": DocFormat.text,
    ".pdf": DocFormat.pdf,
}


def _collapse_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


class _HTMLTextExtractor(HTMLParser):
    """Strips HTML tags to plain text, turning h1-h6 into Markdown headings
    so the output is chunkable the same way as a Markdown source."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._heading_level: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _HEADING_TAGS:
            self._heading_level = _HEADING_TAGS[tag]
            self._parts.append("\n" + "#" * self._heading_level + " ")
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _HEADING_TAGS:
            self._heading_level = None
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text + " ")

    def text(self) -> str:
        return "".join(self._parts)


def load_markdown_file(path: Path) -> NormalizedDocument:
    raw = path.read_text(encoding="utf-8")
    return NormalizedDocument(
        source_name=path.stem,
        doc_format=DocFormat.markdown,
        raw_text=raw,
        cleaned_text=_collapse_whitespace(raw),
    )


def load_html_file(path: Path) -> NormalizedDocument:
    raw = path.read_text(encoding="utf-8")
    extractor = _HTMLTextExtractor()
    extractor.feed(raw)
    return NormalizedDocument(
        source_name=path.stem,
        doc_format=DocFormat.html,
        raw_text=raw,
        cleaned_text=_collapse_whitespace(extractor.text()),
    )


def load_text_file(path: Path) -> NormalizedDocument:
    raw = path.read_text(encoding="utf-8")
    return NormalizedDocument(
        source_name=path.stem,
        doc_format=DocFormat.text,
        raw_text=raw,
        cleaned_text=_collapse_whitespace(raw),
    )


def load_pdf_file(path: Path) -> NormalizedDocument:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]

    raw = "\n\n".join(pages)
    cleaned_parts = [f"## Page {i}\n{text}" for i, text in enumerate(pages, start=1)]
    cleaned = _collapse_whitespace("\n\n".join(cleaned_parts))

    return NormalizedDocument(
        source_name=path.stem,
        doc_format=DocFormat.pdf,
        raw_text=raw,
        cleaned_text=cleaned,
        page_count=len(pages),
    )


_LOADERS = {
    DocFormat.markdown: load_markdown_file,
    DocFormat.html: load_html_file,
    DocFormat.text: load_text_file,
    DocFormat.pdf: load_pdf_file,
}


def normalize_document(path: Path) -> NormalizedDocument:
    """Dispatch to the right loader based on file extension."""
    fmt = SUPPORTED_EXTENSIONS.get(path.suffix.lower())
    if fmt is None:
        raise ValueError(f"Unsupported document format: {path.suffix!r} ({path})")
    return _LOADERS[fmt](path)


def save_normalized(doc: NormalizedDocument, out_dir: Path) -> tuple[Path, Path]:
    """Persist raw and cleaned text side by side for debugging indexing issues."""
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{doc.source_name}.raw.txt"
    clean_path = out_dir / f"{doc.source_name}.clean.txt"
    raw_path.write_text(doc.raw_text, encoding="utf-8")
    clean_path.write_text(doc.cleaned_text, encoding="utf-8")
    return raw_path, clean_path
