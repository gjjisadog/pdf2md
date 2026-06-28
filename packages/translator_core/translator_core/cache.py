from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import TranslationBlock


def translation_cache_key(provider: str, target_lang: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{provider}:{target_lang}:{digest}"


@dataclass(frozen=True)
class CachedTranslation:
    key: str
    block_id: str
    provider: str
    target_lang: str
    source_text: str
    translated_text: str
    created_at: str


class TranslationCacheStore:
    schema_version = 1

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def read(self, key: str) -> CachedTranslation | None:
        if not self.path.exists():
            return None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("key") != key:
                continue
            return CachedTranslation(
                key=str(record.get("key") or ""),
                block_id=str(record.get("block_id") or ""),
                provider=str(record.get("provider") or ""),
                target_lang=str(record.get("target_lang") or ""),
                source_text=str(record.get("source_text") or ""),
                translated_text=str(record.get("translated_text") or ""),
                created_at=str(record.get("created_at") or ""),
            )
        return None

    def write(
        self,
        *,
        key: str,
        block: TranslationBlock,
        translated_text: str,
        provider: str,
        target_lang: str,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "schema_version": self.schema_version,
            "key": key,
            "block_id": block.block_id,
            "provider": provider,
            "target_lang": target_lang,
            "source_text": block.text,
            "translated_text": translated_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
