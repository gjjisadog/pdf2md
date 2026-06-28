"""Source map helpers for tracing Markdown blocks back to OCR output."""

from .generator import build_source_map, normalize_blocks
from .models import OcrBlock

__all__ = ["OcrBlock", "build_source_map", "normalize_blocks"]
