"""Generic OCR HTTP client and output writer for BookMD conversion."""

from .client import MissingOcrConfigError, OcrApiConfig, OcrApiError, OcrHttpClient
from .writer import write_ocr_output

__all__ = [
    "MissingOcrConfigError",
    "OcrApiConfig",
    "OcrApiError",
    "OcrHttpClient",
    "write_ocr_output",
]
