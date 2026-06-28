from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ocr_client import OcrApiConfig, OcrHttpClient, OcrJobClient, write_ocr_output


@dataclass(frozen=True)
class OcrOptions:
    source_pdf: Path
    output_dir: Path


def run_ocr(options: OcrOptions) -> Path:
    if not options.source_pdf.exists():
        raise FileNotFoundError(f"Source PDF does not exist: {options.source_pdf}")
    client = _ocr_client_from_env()
    if hasattr(client, "parse_to_output"):
        return client.parse_to_output(options.source_pdf, options.output_dir)
    response = client.parse_pdf(options.source_pdf)
    return write_ocr_output(response, options.output_dir)


def check_ocr_health() -> dict[str, object]:
    client = _ocr_client_from_env()
    if not hasattr(client, "check_health"):
        return {"status": "unknown", "service": "direct-ocr"}
    return client.check_health()


def _ocr_client_from_env() -> OcrHttpClient | OcrJobClient:
    return OcrJobClient(OcrApiConfig.from_env())
