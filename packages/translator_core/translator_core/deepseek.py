from __future__ import annotations

import os
from dataclasses import dataclass


class MissingApiKeyError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str = "deepseek-v4-flash"
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
            timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "60")),
            retry=int(os.getenv("DEEPSEEK_RETRY", "3")),
        )
