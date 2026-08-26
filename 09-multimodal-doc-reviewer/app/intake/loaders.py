"""Format loaders (Phase 1, step 1): turn uploaded bytes into normalized
`Page` records. PDFs are split by page; born-digital pages (with an
embedded text layer) are extracted directly and skip preprocessing/OCR
entirely, while image-only (scanned) pages are marked `pdf_image` with no
normalized image, since this offline demo has no PDF rasterizer bundled —
they are routed straight to OCR/vision fallback in Phase 2. Raster formats
(PNG/JPEG/TIFF) go through the Phase 1 preprocessing pipeline.
"""
from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings
from app.core.models import PageSourceFormat
from app.intake.models import Page
from app.intake.preprocessing import preprocess_image

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
}


def _load_image_pages(data: bytes) -> list[Page]:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise ValueError("could not decode image data") from exc

    processed, steps, warnings = preprocess_image(
        image, settings.min_page_width_px, settings.min_page_height_px
    )
    buffer = io.BytesIO()
    processed.convert("RGB").save(buffer, format="PNG")

    return [
        Page(
            page_number=1,
            source_format=PageSourceFormat.IMAGE,
            width_px=processed.size[0],
            height_px=processed.size[1],
            normalized_image_png=buffer.getvalue(),
            preprocessing=steps,
            warnings=warnings,
        )
    ]


def _load_pdf_pages(data: bytes) -> list[Page]:
    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise ValueError("could not decode PDF data") from exc

    if not reader.pages:
        raise ValueError("PDF has no pages")

    pages: list[Page] = []
    for index, pdf_page in enumerate(reader.pages, start=1):
        text = (pdf_page.extract_text() or "").strip()
        box = pdf_page.mediabox
        width = int(box.width) if box else None
        height = int(box.height) if box else None

        if text:
            pages.append(
                Page(
                    page_number=index,
                    source_format=PageSourceFormat.PDF_TEXT,
                    width_px=width,
                    height_px=height,
                    embedded_text=text,
                )
            )
        else:
            pages.append(
                Page(
                    page_number=index,
                    source_format=PageSourceFormat.PDF_IMAGE,
                    width_px=width,
                    height_px=height,
                    warnings=[
                        (
                            "scanned page with no embedded text layer; no offline PDF "
                            "rasterizer is bundled, so this page has no normalized image "
                            "and will be routed to vision fallback"
                        )
                    ],
                )
            )
    return pages


def load_pages(data: bytes, content_type: str) -> list[Page]:
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError(
            f"unsupported content type '{content_type}'; use one of {sorted(SUPPORTED_CONTENT_TYPES)}"
        )
    if content_type == "application/pdf":
        return _load_pdf_pages(data)
    return _load_image_pages(data)
