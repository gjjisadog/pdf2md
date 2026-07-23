from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

from source_map_core import build_source_map, normalize_blocks


class OcrApiError(RuntimeError):
    pass


def write_ocr_output(response: Mapping[str, Any], output_dir: Path | str) -> Path:
    normalized = {
        "metadata": dict(response.get("metadata") or {}),
        "blocks": list(response.get("blocks") or []),
        "assets": list(response.get("assets") or []),
    }
    prepared_assets = _prepare_assets(normalized["assets"])
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_assets(prepared_assets, target)
    (target / "result.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_ocr_source_map(normalized, target)
    (target / "result.md").write_text(_render_result_markdown(normalized["blocks"]), encoding="utf-8")
    (target / "parse.log").write_text(
        f"created_at={datetime.now(timezone.utc).isoformat()}\nblocks={len(normalized['blocks'])}\n",
        encoding="utf-8",
    )
    return target


def write_ocr_source_map(result_json: Mapping[str, Any], output_dir: Path | str) -> None:
    target = Path(output_dir)
    source_map = build_source_map(normalize_blocks(result_json), {})
    (target / "source_map.json").write_text(
        json.dumps(source_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _prepare_assets(assets: list[Any]) -> list[tuple[Path, bytes]]:
    prepared_assets: list[tuple[Path, bytes]] = []
    for asset in assets:
        if not isinstance(asset, Mapping):
            continue
        content_base64 = asset.get("content_base64")
        if content_base64 is None:
            continue
        relative_path = asset.get("path")
        if not isinstance(relative_path, str) or not relative_path:
            raise OcrApiError("OCR inline asset must include a non-empty path")
        if not isinstance(content_base64, str):
            raise OcrApiError(f"OCR inline asset content_base64 must be a string: {relative_path!r}")
        safe_path = _safe_asset_path(relative_path)
        try:
            content = base64.b64decode(content_base64, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise OcrApiError(f"OCR inline asset has invalid base64 content: {relative_path!r}") from exc
        prepared_assets.append((safe_path, content))
    return prepared_assets


def _safe_asset_path(relative_path: str) -> Path:
    if "\\" in relative_path:
        raise OcrApiError(f"OCR inline asset path must be a safe relative path: {relative_path!r}")
    candidate = Path(relative_path)
    if (
        candidate.is_absolute()
        or PureWindowsPath(relative_path).is_absolute()
        or any(part in {".", ".."} for part in candidate.parts)
    ):
        raise OcrApiError(f"OCR inline asset path must be a safe relative path: {relative_path!r}")

    parts = candidate.parts
    if not parts:
        raise OcrApiError("OCR inline asset must include a non-empty path")
    if parts[0] == "assets":
        parts = parts[1:]
    if not parts:
        raise OcrApiError(f"OCR inline asset path must name a file under assets/: {relative_path!r}")
    return Path(*parts)


def _write_assets(assets: list[tuple[Path, bytes]], output_dir: Path) -> None:
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    assets_root = assets_dir.resolve()
    for relative_path, content in assets:
        asset_path = assets_dir / relative_path
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            asset_path.resolve().relative_to(assets_root)
        except ValueError as exc:
            raise OcrApiError(f"OCR inline asset path escapes assets directory: {relative_path!s}") from exc
        asset_path.write_bytes(content)


def _render_result_markdown(blocks: list[Any]) -> str:
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        text = str(block.get("text") or "")
        block_type = str(block.get("type") or "paragraph").lower()
        if not text and block_type not in {"formula", "figure", "table"}:
            continue
        if block_type == "heading":
            level = min(max(int(block.get("level") or 1), 1), 6)
            parts.append(f"{'#' * level} {text}".rstrip())
        elif block_type == "formula" and block.get("latex"):
            parts.append(f"$$\n{block['latex']}\n$$")
        elif block_type == "table" and block.get("markdown"):
            parts.append(str(block["markdown"]))
        elif block_type in {"figure", "table", "formula"} and _asset_path(block):
            parts.append(_render_asset_directive(block_type, block))
        else:
            parts.append(text)
    return "\n\n".join(parts).rstrip() + "\n"


def _asset_path(block: Mapping[str, Any]) -> str:
    return str(
        block.get("asset_path")
        or block.get("image_path")
        or block.get("formula_path")
        or block.get("table_path")
        or block.get("src")
        or ""
    )


def _render_asset_directive(block_type: str, block: Mapping[str, Any]) -> str:
    block_id = str(block.get("block_id") or "")
    src = _asset_path(block)
    page = str(block.get("page") or 1)
    caption = str(block.get("caption") or block.get("text") or "")
    return f':::{block_type} id="{block_id}" src="../{src}" page="{page}"\n{caption}\n:::'
