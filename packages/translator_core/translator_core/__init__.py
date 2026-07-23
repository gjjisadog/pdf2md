"""Translation interfaces and provider implementations for BookMD."""

from .cache import CachedTranslation, TranslationCacheStore, translation_cache_key
from .deepseek import (
    DeepSeekConfig,
    DeepSeekConfigError,
    DeepSeekTranslator,
    MalformedTranslationError,
    MissingApiKeyError,
)
from .models import TranslationBlock, TranslationResult
from .noop import NoopTranslator
from .terms import extract_terms

__all__ = [
    "CachedTranslation",
    "DeepSeekConfig",
    "DeepSeekConfigError",
    "DeepSeekTranslator",
    "MalformedTranslationError",
    "MissingApiKeyError",
    "NoopTranslator",
    "TranslationCacheStore",
    "TranslationBlock",
    "TranslationResult",
    "extract_terms",
    "translation_cache_key",
]
