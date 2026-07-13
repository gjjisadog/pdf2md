"""Cross-platform PDF rendering and image cropping for BookMD assets."""

from __future__ import annotations

import math
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


def render_pdf_page(
    source_pdf: str | Path,
    page: int,
    output_path: str | Path,
    *,
    scale: float = 2.0,
) -> Path:
    """Render one 1-based PDF page to a PNG using PDFium."""

    if page < 1:
        raise ValueError("PDF page numbers are 1-based")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("PDF render scale must be positive")

    source = Path(source_pdf)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    document = None
    pdf_page = None
    bitmap = None
    try:
        document = pdfium.PdfDocument(str(source))
        if page > len(document):
            raise ValueError(f"PDF page {page} is outside document with {len(document)} pages")
        pdf_page = document[page - 1]
        bitmap = pdf_page.render(scale=scale)
        pil_image = bitmap.to_pil()
        try:
            pil_image.save(output, format="PNG")
        finally:
            pil_image.close()
    except Exception as exc:
        raise RuntimeError(f"PDFium failed to render page {page} from {source}: {exc}") from exc
    finally:
        if bitmap is not None:
            bitmap.close()
        if pdf_page is not None:
            pdf_page.close()
        if document is not None:
            document.close()
    return output


def crop_image(
    page_image: str | Path,
    bbox: list[float],
    output_path: str | Path,
    *,
    margin: int = 8,
) -> bool:
    """Crop an OCR bounding box from a page image using Pillow."""

    with Image.open(page_image) as source_image:
        crop_box = _crop_box(bbox, source_image.size, margin=margin)
    if crop_box is None:
        return False
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(page_image) as image:
            image.load()
            image.crop(crop_box).save(output, format="PNG")
    except (OSError, ValueError):
        return False
    return output.exists()


def _crop_box(
    bbox: list[float],
    image_size: tuple[int, int],
    *,
    margin: int,
) -> tuple[int, int, int, int] | None:
    try:
        x1, y1, x2, y2 = [float(value) for value in bbox[:4]]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in (x1, y1, x2, y2)) or x2 <= x1 or y2 <= y1:
        return None
    width, height = image_size
    if x2 > width or y2 > height:
        scale = min(width / max(x2, 1), height / max(y2, 1))
        x1, y1, x2, y2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
    left = max(0, int(x1) - margin)
    top = max(0, int(y1) - margin)
    right = min(width, int(x2) + margin)
    bottom = min(height, int(y2) + margin)
    if right - left < 4 or bottom - top < 4:
        return None
    return left, top, right, bottom
