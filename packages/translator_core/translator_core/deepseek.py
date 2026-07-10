from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable
from urllib import request
from urllib.error import URLError

from .models import TranslationBlock, TranslationResult


class MissingApiKeyError(RuntimeError):
    pass


class MalformedTranslationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com/chat/completions"
    timeout: int = 60
    retry: int = 3
    temperature: float = 0.2
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "DeepSeekConfig":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise MissingApiKeyError(
                "DEEPSEEK_API_KEY is required when provider is deepseek"
            )
        return cls(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
            timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "60")),
            retry=int(os.getenv("DEEPSEEK_RETRY", "3")),
            temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096")),
        )


Transport = Callable[[dict[str, Any], DeepSeekConfig], dict[str, Any]]


class DeepSeekTranslator:
    def __init__(self, config: DeepSeekConfig, transport: Transport | None = None):
        self.config = config
        self.transport = transport or _http_transport

    def translate_blocks(
        self,
        blocks: list[TranslationBlock],
        target_lang: str,
        terms: list[dict[str, str]] | None = None,
    ) -> list[TranslationResult]:
        if not blocks:
            return []

        payload = _build_payload(blocks, target_lang, terms or [], self.config)
        response = self._send_with_retry(payload)
        return _parse_response(response, blocks)

    def _send_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = max(1, self.config.retry)
        for _ in range(attempts):
            try:
                return self.transport(payload, self.config)
            except (OSError, URLError) as exc:
                last_error = exc
        raise RuntimeError(f"DeepSeek request failed after {attempts} attempt(s): {last_error}") from last_error


def _build_payload(
    blocks: list[TranslationBlock],
    target_lang: str,
    terms: list[dict[str, str]],
    config: DeepSeekConfig,
) -> dict[str, Any]:
    source_payload = {
        "target_lang": target_lang,
        "rules": [
            "Return JSON only.",
            "Preserve block_id exactly.",
            "Do not change formulas, variable names, units, figure/table numbers, Markdown links, or code.",
            "Keep one translated_text for every input block.",
        ],
        "terms": terms,
        "blocks": [
            {"block_id": block.block_id, "text": block.text}
            for block in blocks
        ],
    }
    return {
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You translate professional PDF OCR blocks into precise target-language Markdown. "
                    "Always return a JSON object with a blocks array."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(source_payload, ensure_ascii=False),
            },
        ],
    }


def _parse_response(
    response: dict[str, Any],
    source_blocks: list[TranslationBlock],
) -> list[TranslationResult]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise MalformedTranslationError("DeepSeek response is missing choices[0].message.content") from exc

    if isinstance(content, str):
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise MalformedTranslationError(f"DeepSeek response content is not JSON: {exc}") from exc
    elif isinstance(content, dict):
        payload = content
    else:
        raise MalformedTranslationError("DeepSeek response content must be a JSON object or string")

    raw_blocks = payload.get("blocks")
    if not isinstance(raw_blocks, list):
        raise MalformedTranslationError("DeepSeek response JSON must contain a blocks array")

    by_id: dict[str, str] = {}
    for item in raw_blocks:
        if not isinstance(item, dict):
            raise MalformedTranslationError("DeepSeek response block entries must be objects")
        block_id = str(item.get("block_id") or "")
        translated_text = item.get("translated_text")
        if not block_id or translated_text is None:
            raise MalformedTranslationError("Each DeepSeek response block needs block_id and translated_text")
        by_id[block_id] = str(translated_text)

    results: list[TranslationResult] = []
    missing: list[str] = []
    for block in source_blocks:
        if block.block_id not in by_id:
            missing.append(block.block_id)
            continue
        results.append(
            TranslationResult(
                block_id=block.block_id,
                source_text=block.text,
                translated_text=by_id[block.block_id],
            )
        )
    if missing:
        raise MalformedTranslationError(f"DeepSeek response missed block_id(s): {', '.join(missing)}")
    return results


def _http_transport(payload: dict[str, Any], config: DeepSeekConfig) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        config.base_url,
        data=body,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "pdf2md-converter/0.1",
        },
        method="POST",
    )
    with request.urlopen(http_request, timeout=config.timeout) as response:
        return json.loads(response.read().decode("utf-8"))
