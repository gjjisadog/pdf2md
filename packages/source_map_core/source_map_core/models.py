from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OcrBlock:
    block_id: str
    page: int
    type: str
    bbox: list[float]
    text: str = ""
    level: int | None = None
    asset_path: str | None = None
    latex: str | None = None
    markdown: str | None = None
    caption: str | None = None
    translated_text: str | None = None
