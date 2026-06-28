from __future__ import annotations

import json

from source_map_core import OcrBlock


def render_block_markdown(block: OcrBlock, bilingual: bool = False) -> str:
    body = _render_body(block, bilingual=bilingual)
    return f"{_trace_comment(block)}\n{body}".rstrip() + "\n"


def _trace_comment(block: OcrBlock) -> str:
    bbox = json.dumps(block.bbox, ensure_ascii=False)
    return f"<!-- block_id: {block.block_id}; page: {block.page}; bbox: {bbox} -->"


def _render_body(block: OcrBlock, bilingual: bool = False) -> str:
    block_type = block.type.lower()
    if block_type == "heading":
        level = min(max(block.level or 1, 1), 6)
        text = _display_text(block, bilingual)
        return f"{'#' * level} {text}".rstrip()
    if block_type == "formula":
        if block.latex:
            return f"$$\n{block.latex}\n$$"
        return _render_asset_block("formula", block)
    if block_type == "figure":
        return _render_asset_block("figure", block)
    if block_type == "table":
        if block.markdown:
            return block.markdown
        return _render_asset_block("table", block)
    if block_type == "footnote":
        return _display_text(block, bilingual)
    if block_type == "caption":
        return block.caption or _display_text(block, bilingual)
    return _display_text(block, bilingual)


def _display_text(block: OcrBlock, bilingual: bool) -> str:
    if bilingual and block.translated_text and block.translated_text != block.text:
        return f"{block.translated_text}\n\n原文: {block.text}"
    return block.translated_text or block.text


def _render_asset_block(kind: str, block: OcrBlock) -> str:
    src = block.asset_path or ""
    caption = block.caption or block.text
    page_attr = f' page="{block.page}"'
    return f':::{kind} id="{block.block_id}" src="../{src}"{page_attr}\n{caption}\n:::'
