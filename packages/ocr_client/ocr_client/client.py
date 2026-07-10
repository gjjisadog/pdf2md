from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from .writer import write_ocr_source_map


class MissingOcrConfigError(RuntimeError):
    pass


class OcrApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class OcrApiConfig:
    api_url: str
    api_key: str = ""
    timeout: int = 120
    device: str = "gpu"

    @classmethod
    def from_env(cls, timeout: int | None = None) -> "OcrApiConfig":
        api_url = os.getenv("OCR_API_URL")
        if not api_url:
            raise MissingOcrConfigError("OCR_API_URL is required for OCR API calls")
        return cls(
            api_url=api_url,
            api_key=os.getenv("OCR_API_KEY", ""),
            timeout=_positive_int(timeout, "timeout") if timeout is not None else _env_positive_int("OCR_API_TIMEOUT", 120),
            device=os.getenv("OCR_API_DEVICE", "gpu"),
        )


Transport = Callable[[bytes, str, OcrApiConfig], Mapping[str, Any]]
HealthTransport = Callable[[OcrApiConfig], Mapping[str, Any]]
JobSubmitTransport = Callable[[bytes, str, OcrApiConfig], Mapping[str, Any]]
DownloadTransport = Callable[[str, OcrApiConfig], bytes]
StatusTransport = Callable[[str, OcrApiConfig], Mapping[str, Any]]


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise MissingOcrConfigError(f"{name} must be an integer") from exc
    if value < 1:
        raise MissingOcrConfigError(f"{name} must be greater than 0")
    return value


def _positive_int(value: int, name: str) -> int:
    if value < 1:
        raise MissingOcrConfigError(f"{name} must be greater than 0")
    return value


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


class OcrJobClient:
    def __init__(
        self,
        config: OcrApiConfig,
        health_transport: HealthTransport | None = None,
        submit_transport: JobSubmitTransport | None = None,
        status_transport: StatusTransport | None = None,
        download_transport: DownloadTransport | None = None,
        poll_interval_seconds: float = 2.0,
        max_polls: int = 60,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
    ):
        self.config = config
        self.health_transport = health_transport or _job_health_transport
        self.submit_transport = submit_transport or _job_submit_transport
        self.status_transport = status_transport or _job_status_transport
        self.download_transport = download_transport or _job_download_transport
        self.poll_interval_seconds = poll_interval_seconds
        self.max_polls = max_polls
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

    def check_health(self) -> dict[str, Any]:
        response = dict(self.health_transport(self.config))
        if response.get("status") != "ok":
            raise OcrApiError(f"OCR service health check failed: {response}")
        return response

    def parse_to_output(self, source_pdf: str | os.PathLike[str], output_dir: str | os.PathLike[str]) -> Path:
        path = os.fspath(source_pdf)
        with open(path, "rb") as handle:
            pdf_bytes = handle.read()
        job = self._wait_for_success(self.submit_transport(pdf_bytes, os.path.basename(path), self.config))
        files = _job_files(job)
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / "assets").mkdir(exist_ok=True)
        downloads = {
            "result_md": "result.md",
            "result_json": "result.json",
            "source_map": "source_map.json",
            "parse_log": "parse.log",
        }
        for key, filename in downloads.items():
            file_url = files.get(key)
            if not file_url:
                if key == "source_map":
                    continue
                raise OcrApiError(f"OCR job response missing file URL: {key}")
            content = self._with_retries(lambda: self.download_transport(str(file_url), self.config))
            (target / filename).write_bytes(content)
        _ensure_source_map_aligned(target)
        if not (target / "parse.log").exists():
            (target / "parse.log").write_text(f"job_id={job.get('job_id', '')}\n", encoding="utf-8")
        return target

    def _wait_for_success(self, job: Mapping[str, Any]) -> Mapping[str, Any]:
        status = job.get("status")
        if status == "succeeded":
            return job
        job_id = str(job.get("job_id") or "")
        if not job_id:
            raise OcrApiError(f"OCR job response missing job_id: {job}")
        for _ in range(self.max_polls):
            if status in {"failed", "error", "cancelled"}:
                raise OcrApiError(f"OCR job did not succeed: {job}")
            if self.poll_interval_seconds:
                time.sleep(self.poll_interval_seconds)
            job = self._with_retries(lambda: self.status_transport(job_id, self.config))
            status = job.get("status")
            if status == "succeeded":
                return job
        raise OcrApiError(f"OCR job timed out waiting for success: {job_id}")

    def _with_retries(self, operation: Callable[[], Any]) -> Any:
        last_error: BaseException | None = None
        attempts = max(1, self.retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except (OSError, URLError) as exc:
                if isinstance(exc, HTTPError) and not _is_retryable_http_error(exc):
                    raise
                last_error = exc
                if attempt == attempts:
                    break
                if self.retry_delay_seconds:
                    time.sleep(self.retry_delay_seconds)
        assert last_error is not None
        raise last_error


def _is_retryable_http_error(error: HTTPError) -> bool:
    return error.code >= 500 or error.code in {408, 429}


def _job_files(job: Mapping[str, Any]) -> Mapping[str, Any]:
    if job.get("status") != "succeeded":
        raise OcrApiError(f"OCR job did not succeed: {job}")
    files = job.get("files")
    if not isinstance(files, Mapping):
        raise OcrApiError("OCR job response must contain files object")
    return files


def _ensure_source_map_aligned(output_dir: Path) -> None:
    result_json_path = output_dir / "result.json"
    if not result_json_path.exists():
        return
    result_json = _read_job_result_json(result_json_path)
    expected_blocks = _ocr_block_count(result_json)
    source_map_path = output_dir / "source_map.json"
    if source_map_path.exists():
        try:
            source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            write_ocr_source_map(result_json, output_dir)
            return
        source_map_blocks = source_map.get("blocks") or []
        if len(source_map_blocks) == expected_blocks and _source_map_signature(source_map_blocks) == _ocr_block_signature(result_json):
            return
    write_ocr_source_map(result_json, output_dir)


def _read_job_result_json(path: Path) -> Mapping[str, Any]:
    try:
        result_json = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OcrApiError(f"OCR job result.json is not valid JSON: {exc}") from exc
    if not isinstance(result_json, Mapping):
        raise OcrApiError("OCR job result.json must be a JSON object")
    return result_json


def _ocr_block_count(result_json: Mapping[str, Any]) -> int:
    if isinstance(result_json.get("pages"), list):
        return sum(
            len(page.get("blocks") or [])
            for page in result_json["pages"]
            if isinstance(page, Mapping)
        )
    return len(result_json.get("blocks") or [])


def _ocr_block_signature(result_json: Mapping[str, Any]) -> list[tuple[str, int, tuple[Any, ...], str]]:
    if isinstance(result_json.get("pages"), list):
        signature: list[tuple[str, int, tuple[Any, ...], str]] = []
        for page in result_json["pages"]:
            if not isinstance(page, Mapping):
                continue
            page_number = int(
                page.get("page")
                or page.get("page_number")
                or page.get("page_index")
                or 1
            )
            for block in page.get("blocks") or []:
                if isinstance(block, Mapping):
                    signature.append((
                        str(block.get("block_id") or block.get("id") or ""),
                        int(block.get("page") or block.get("page_number") or page_number),
                        tuple(block.get("bbox") or []),
                        str(block.get("text") or ""),
                    ))
        return signature
    return [
        (
            str(block.get("block_id") or block.get("id") or ""),
            int(block.get("page") or block.get("page_number") or 1),
            tuple(block.get("bbox") or []),
            str(block.get("text") or ""),
        )
        for block in result_json.get("blocks") or []
        if isinstance(block, Mapping)
    ]


def _source_map_signature(blocks: list[Any]) -> list[tuple[str, int, tuple[Any, ...], str]]:
    return [
        (
            str(block.get("block_id") or ""),
            int(block.get("source_page") or block.get("page") or 1),
            tuple(block.get("bbox") or []),
            str(block.get("source_text") or ""),
        )
        for block in blocks
        if isinstance(block, Mapping)
    ]


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
    with _urlopen(http_request, timeout=config.timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _job_health_transport(config: OcrApiConfig) -> dict[str, Any]:
    http_request = request.Request(
        _service_url(config, "/health"),
        headers=_auth_headers(config),
        method="GET",
    )
    with _urlopen(http_request, timeout=config.timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _job_submit_transport(pdf_bytes: bytes, filename: str, config: OcrApiConfig) -> dict[str, Any]:
    boundary = f"----bookmd-ocr-{uuid.uuid4().hex}"
    body = _multipart_body(boundary, "file", filename, pdf_bytes, fields={"device": config.device})
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        **_auth_headers(config),
    }
    http_request = request.Request(
        _service_url(config, "/v1/ocr/parse"),
        data=body,
        headers=headers,
        method="POST",
    )
    with _urlopen(http_request, timeout=config.timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _job_status_transport(job_id: str, config: OcrApiConfig) -> dict[str, Any]:
    http_request = request.Request(
        _service_url(config, f"/v1/jobs/{job_id}"),
        headers=_auth_headers(config),
        method="GET",
    )
    with _urlopen(http_request, timeout=config.timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _job_download_transport(file_url: str, config: OcrApiConfig) -> bytes:
    http_request = request.Request(
        _service_url(config, file_url),
        headers=_auth_headers(config),
        method="GET",
    )
    with _urlopen(http_request, timeout=config.timeout) as response:
        return response.read()


def _auth_headers(config: OcrApiConfig) -> dict[str, str]:
    if not config.api_key:
        return {}
    return {"Authorization": f"Bearer {config.api_key}"}


def _urlopen(http_request: request.Request, timeout: int):
    opener = request.build_opener(request.ProxyHandler({}))
    return opener.open(http_request, timeout=timeout)


def _service_url(config: OcrApiConfig, path: str) -> str:
    base_url = config.api_url.rstrip("/") + "/"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(base_url, path.lstrip("/"))


def _multipart_body(
    boundary: str,
    field_name: str,
    filename: str,
    payload: bytes,
    fields: Mapping[str, str] | None = None,
) -> bytes:
    parts: list[bytes] = []
    for key, value in (fields or {}).items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return b"".join(parts) + head + payload + tail
