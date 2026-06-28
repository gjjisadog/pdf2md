from __future__ import annotations

import hashlib


def translation_cache_key(provider: str, target_lang: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{provider}:{target_lang}:{digest}"
