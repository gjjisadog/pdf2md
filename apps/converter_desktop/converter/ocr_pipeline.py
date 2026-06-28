from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ocr_client import OcrApiConfig, OcrHttpClient, write_ocr_output


@dataclass(frozen=True)
class OcrOptions:
    source_pdf: Path
    output_dir: Path


def run_ocr(options: OcrOptions) -> Path:
    if not options.source_pdf.exists():
        raise FileNotFoundError(f"Source PDF does not exist: {options.source_pdf}")
    client = _ocr_client_from_env()
    response = client.parse_pdf(options.source_pdf)
    return write_ocr_output(response, options.output_dir)


def _ocr_client_from_env() -> OcrHttpClient:
    return OcrHttpClient(OcrApiConfig.from_env())
