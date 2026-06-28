import pytest

from translator_core import (
    DeepSeekConfig,
    MissingApiKeyError,
    NoopTranslator,
    TranslationBlock,
)


def test_noop_translator_preserves_block_alignment():
    result = NoopTranslator().translate_blocks(
        [TranslationBlock(block_id="b1", text="Voltage source inverter")],
        target_lang="zh",
    )

    assert result[0].block_id == "b1"
    assert result[0].translated_text == "Voltage source inverter"


def test_deepseek_config_requires_api_key_when_enabled(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(MissingApiKeyError):
        DeepSeekConfig.from_env()
