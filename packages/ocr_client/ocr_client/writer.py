from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_ocr_output(response: Mapping[str, Any], output_dir: Path | str) -> Path:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "assets").mkdir(exist_ok=True)

    normalized = {
        "metadata": dict(response.get("metadata") or {}),
        "blocks": list(response.get("blocks") or []),
        "assets": list(response.get("assets") or []),
    }
    _write_assets(normalized["assets"], target)
    (target / "result.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (target / "result.md").write_text(_render_result_markdown(normalized["blocks"]), encoding="utf-8")
    (target / "parse.log").write_text(
        f"created_at={datetime.now(timezone.utc).isoformat()}\nblocks={len(normalized['blocks'])}\n",
        encoding="utf-8",
    )
    return target


def _write_assets(assets: list[Any], output_dir: Path) -> None:
    for asset in assets:
        if not isinstance(asset, Mapping):
            continue
        relative_path = str(asset.get("path") or "")
        content_base64 = asset.get("content_base64")
        if not relative_path or not isinstance(content_base64, str):
            continue
        asset_path = output_dir / relative_path
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(base64.b64decode(content_base64))


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
