from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib import request


class MissingOcrConfigError(RuntimeError):
    pass


class OcrApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class OcrApiConfig:
    api_url: str
    api_key: str = ""
    timeout: int = 120

    @classmethod
    def from_env(cls) -> "OcrApiConfig":
        api_url = os.getenv("OCR_API_URL")
        if not api_url:
            raise MissingOcrConfigError("OCR_API_URL is required for OCR API calls")
        return cls(
            api_url=api_url,
            api_key=os.getenv("OCR_API_KEY", ""),
            timeout=int(os.getenv("OCR_API_TIMEOUT", "120")),
        )


Transport = Callable[[bytes, str, OcrApiConfig], Mapping[str, Any]]


class OcrHttpClient:
    def __init__(self, config: OcrApiConfig, transport: Transport | None = None):
        self.config = config
        self.transport = transport or _http_transport

    def parse_pdf(self, source_pdf: str | os.PathLike[str]) -> dict[str, Any]:
        path = os.fspath(source_pdf)
        with open(path, "rb") as handle:
            pdf_bytes = handle.read()
        response = self.transport(pdf_bytes, os.path.basename(path), self.config)
        return _normalize_response(response)


def _normalize_response(response: Mapping[str, Any]) -> dict[str, Any]:
    metadata = response.get("metadata")
    blocks = response.get("blocks")
    assets = response.get("assets", [])
    if metadata is not None and not isinstance(metadata, Mapping):
        raise OcrApiError("OCR response metadata must be an object")
    if not isinstance(blocks, list):
        raise OcrApiError("OCR response must contain a blocks array")
    if not isinstance(assets, list):
        raise OcrApiError("OCR response assets must be an array when present")

    normalized_blocks: list[dict[str, Any]] = []
    for index, raw_block in enumerate(blocks, start=1):
        if not isinstance(raw_block, Mapping):
            raise OcrApiError("OCR response block entries must be objects")
        block_id = str(raw_block.get("block_id") or raw_block.get("id") or f"b{index:04d}")
        normalized_blocks.append(
            {
                "block_id": block_id,
                "page": int(raw_block.get("page") or raw_block.get("page_number") or 1),
                "type": str(raw_block.get("type") or "paragraph"),
                "text": str(raw_block.get("text") or ""),
                "bbox": list(raw_block.get("bbox") or []),
                **_optional_block_fields(raw_block),
            }
        )

    return {
        "metadata": dict(metadata or {}),
        "blocks": normalized_blocks,
        "assets": list(assets),
    }


def _optional_block_fields(raw_block: Mapping[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in ("level", "asset_path", "image_path", "formula_path", "table_path", "src", "latex", "markdown", "caption"):
        value = raw_block.get(key)
        if value is not None and value != "":
            fields[key] = value
    return fields


def _http_transport(pdf_bytes: bytes, filename: str, config: OcrApiConfig) -> dict[str, Any]:
    boundary = f"----bookmd-ocr-{uuid.uuid4().hex}"
    body = _multipart_body(boundary, "file", filename, pdf_bytes)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    http_request = request.Request(
        config.api_url,
        data=body,
        headers=headers,
        method="POST",
    )
    with request.urlopen(http_request, timeout=config.timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _multipart_body(boundary: str, field_name: str, filename: str, payload: bytes) -> bytes:
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + payload + tail
