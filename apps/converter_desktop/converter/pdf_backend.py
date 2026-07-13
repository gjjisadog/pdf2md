"""Portable PDF page selection, rendering, and image cropping."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from bookmd_core.visuals import crop_image, render_pdf_page


class PdfBackendError(RuntimeError):
    """A PDF backend operation failed with a source/page-aware message."""


class PdfBackend(Protocol):
    def page_count(self, source_pdf: Path) -> int: ...

    def split_pages(
        self,
        source_pdf: Path,
        first_page: int,
        page_count: int,
        output: Path,
    ) -> Path: ...

    def render_page(
        self,
        source_pdf: Path,
        page: int,
        dpi: int,
        output_dir: Path,
    ) -> Path | None: ...

    def crop_region(self, page_image: Path, bbox: list[float], output: Path) -> bool: ...


class PortablePdfBackend:
    def page_count(self, source_pdf: Path) -> int:
        try:
            import pypdfium2 as pdfium

            document = pdfium.PdfDocument(str(source_pdf))
            try:
                return len(document)
            finally:
                document.close()
        except Exception as exc:
            raise PdfBackendError(f"PDF page_count failed for {source_pdf}: {exc}") from exc

    def split_pages(
        self,
        source_pdf: Path,
        first_page: int,
        page_count: int,
        output: Path,
    ) -> Path:
        if first_page < 1 or page_count < 1:
            raise PdfBackendError(
                f"PDF split requires first_page >= 1 and page_count >= 1: {first_page}, {page_count}"
            )
        try:
            from pypdf import PdfReader, PdfWriter

            reader = PdfReader(str(source_pdf))
            start = first_page - 1
            end = min(start + page_count, len(reader.pages))
            if start >= len(reader.pages) or start >= end:
                raise PdfBackendError(
                    f"PDF split range is outside {source_pdf}: first_page={first_page}, page_count={page_count}"
                )
            writer = PdfWriter()
            for page_index in range(start, end):
                writer.add_page(reader.pages[page_index])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("wb") as handle:
                writer.write(handle)
            return output
        except PdfBackendError:
            raise
        except Exception as exc:
            raise PdfBackendError(f"PDF split failed for {source_pdf}: {exc}") from exc

    def render_page(
        self,
        source_pdf: Path,
        page: int,
        dpi: int,
        output_dir: Path,
    ) -> Path | None:
        if dpi <= 0:
            raise PdfBackendError(f"PDF render dpi must be positive: {dpi}")
        output = output_dir / f"page_{page:03d}.png"
        try:
            return render_pdf_page(source_pdf, page, output, scale=dpi / 72.0)
        except Exception as exc:
            raise PdfBackendError(
                f"PDF render failed for {source_pdf}, page {page}: {exc}"
            ) from exc

    def crop_region(self, page_image: Path, bbox: list[float], output: Path) -> bool:
        return crop_image(page_image, bbox, output)


_BACKEND = PortablePdfBackend()


def get_pdf_backend() -> PdfBackend:
    return _BACKEND
