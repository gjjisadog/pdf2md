from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranslationBlock:
    block_id: str
    text: str


@dataclass(frozen=True)
class TranslationResult:
    block_id: str
    source_text: str
    translated_text: str
