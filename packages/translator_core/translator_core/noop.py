from __future__ import annotations

from collections.abc import Sequence

from .models import TranslationBlock, TranslationResult


class NoopTranslator:
    def translate_blocks(
        self,
        blocks: Sequence[TranslationBlock],
        target_lang: str,
    ) -> list[TranslationResult]:
        return [
            TranslationResult(
                block_id=block.block_id,
                source_text=block.text,
                translated_text=block.text,
            )
            for block in blocks
        ]
