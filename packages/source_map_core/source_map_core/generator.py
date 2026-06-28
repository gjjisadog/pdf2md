from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .models import OcrBlock


def normalize_blocks(data: Mapping[str, Any]) -> list[OcrBlock]:
    raw_blocks: list[tuple[int, Mapping[str, Any]]] = []

    if isinstance(data.get("pages"), Sequence):
        for page_item in data["pages"]:
            if not isinstance(page_item, Mapping):
                continue
            page_number = int(
                page_item.get("page")
                or page_item.get("page_number")
                or page_item.get("page_index")
                or 1
            )
            for block in page_item.get("blocks") or []:
                if isinstance(block, Mapping):
                    raw_blocks.append((page_number, block))
    else:
        for block in data.get("blocks") or []:
            if not isinstance(block, Mapping):
                continue
            page_number = int(block.get("page") or block.get("page_number") or 1)
            raw_blocks.append((page_number, block))

    blocks: list[OcrBlock] = []
    for index, (page_number, block) in enumerate(raw_blocks, start=1):
        block_id = str(
            block.get("block_id")
            or block.get("id")
            or f"p{page_number:03d}_b{index:03d}"
        )
        bbox = block.get("bbox") or []
        blocks.append(
            OcrBlock(
                block_id=block_id,
                page=page_number,
                type=str(block.get("type") or "paragraph"),
                bbox=list(bbox),
                text=str(block.get("text") or ""),
                level=_optional_int(block.get("level")),
                asset_path=_optional_str(
                    block.get("asset_path")
                    or block.get("image_path")
                    or block.get("formula_path")
                    or block.get("table_path")
                    or block.get("src")
                ),
                latex=_optional_str(block.get("latex")),
                markdown=_optional_str(block.get("markdown")),
                caption=_optional_str(block.get("caption")),
                translated_text=_optional_str(block.get("translated_text")),
            )
        )

    return blocks


def build_source_map(
    blocks: Sequence[OcrBlock],
    chapter_by_block: Mapping[str, tuple[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []

    for block in blocks:
        chapter_id, markdown_path = chapter_by_block.get(block.block_id, ("", ""))
        entries.append(
            {
                "block_id": block.block_id,
                "chapter_id": chapter_id,
                "markdown_path": markdown_path,
                "source_page": block.page,
                "bbox": block.bbox,
                "source_text": block.text,
                "translated_text": block.translated_text or "",
                "type": block.type,
            }
        )

    return {"blocks": entries}


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
