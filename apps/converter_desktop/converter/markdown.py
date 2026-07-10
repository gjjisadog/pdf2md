from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import json
import re

from source_map_core import OcrBlock


OCR_TEXT_REPAIRS = (
    (re.compile(r"\bAstraightforwardwayisto\b"), "A straightforward way is to"),
    (re.compile(r"\btheinverter\b", flags=re.IGNORECASE), "the inverter"),
    (re.compile(r"\bvoltageynchronization\b", flags=re.IGNORECASE), "voltage synchronization"),
)


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
        if block.asset_path:
            return _render_asset_block("formula", block)
        latex = block.latex or _text_latex(block.text)
        if latex:
            return f"$$\n{latex}\n$$"
        return _render_asset_block("formula", block)
    if block_type == "figure":
        return _render_asset_block("figure", block)
    if block_type == "table":
        if block.asset_path:
            return _render_asset_block("table", block)
        if block.markdown:
            if _looks_like_html_table(block.markdown):
                return _html_table_to_markdown(block.markdown)
            return block.markdown
        if _looks_like_html_table(block.text):
            return _html_table_to_markdown(block.text)
        return _render_asset_block("table", block)
    if block_type == "footnote":
        return _display_text(block, bilingual)
    if block_type == "caption":
        return block.caption or _display_text(block, bilingual)
    return _display_text(block, bilingual)


def _display_text(block: OcrBlock, bilingual: bool) -> str:
    if bilingual and block.translated_text and block.translated_text != block.text:
        return f"{_normalize_ocr_display_text(block.translated_text)}\n\n原文: {_normalize_ocr_display_text(block.text)}"
    return _normalize_ocr_display_text(block.translated_text or block.text)


def _normalize_ocr_display_text(text: str) -> str:
    normalized = text.replace("\u00ad", "")
    normalized = re.sub(r"([A-Za-z])-\s*\n\s*([A-Za-z])", r"\1-\2", normalized)
    normalized = re.sub(r"(?<!\n)\n(?!\n)", " ", normalized)
    normalized = re.sub(r"(/\s*\d{1,3})(?=\d{1,2}(?:\.\d+)+[A-Za-z])", r"\1 ", normalized)
    normalized = re.sub(r"\b(\d{1,2}(?:\.\d+)+)(?=[A-Za-z])", r"\1 ", normalized)
    for pattern, replacement in OCR_TEXT_REPAIRS:
        normalized = pattern.sub(replacement, normalized)
    normalized = re.sub(r"(?<![\u4e00-\u9fff])([,.;:])(?=[A-Za-z])", r"\1 ", normalized)
    return normalized


def _render_asset_block(kind: str, block: OcrBlock) -> str:
    caption = block.caption or _asset_caption(block.text)
    if not block.asset_path:
        return caption
    page_attr = f' page="{block.page}"'
    return f':::{kind} id="{block.block_id}" src="../{block.asset_path}"{page_attr}\n{caption}\n:::'


def _asset_caption(text: str) -> str:
    if _looks_like_html_table(text):
        text = unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def _text_latex(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if re.search(r"\\(?:begin|frac|sum|int|mathbf|mathrm|left|right|cos|sin|delta|omega)\b", stripped):
        return stripped
    if re.search(r"[_^]\{[^}]+\}", stripped) and "\\" in stripped:
        return stripped
    return ""


def _looks_like_html_table(text: str) -> bool:
    lowered = text.lower()
    return "<table" in lowered and "</table>" in lowered


def _html_table_to_markdown(text: str) -> str:
    rows = _HtmlTableParser.parse(text)
    rows = [[_escape_markdown_table_cell(cell) for cell in row] for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return unescape(re.sub(r"<[^>]+>", " ", text)).strip()
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = normalized[0]
    separator = ["---"] * width
    body = normalized[1:]
    lines = [_markdown_table_row(header), _markdown_table_row(separator)]
    lines.extend(_markdown_table_row(row) for row in body)
    return "\n".join(lines)


def _markdown_table_row(row: list[str]) -> str:
    return "| " + " | ".join(row) + " |"


def _escape_markdown_table_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().replace("|", "\\|")


class _HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    @classmethod
    def parse(cls, text: str) -> list[list[str]]:
        parser = cls()
        parser.feed(text)
        parser.close()
        return parser.rows

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_row is not None and self._current_cell is not None:
            self._current_row.append(unescape("".join(self._current_cell)).strip())
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            self.rows.append(self._current_row)
            self._current_row = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)
