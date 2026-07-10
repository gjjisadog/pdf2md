import pytest

from translator_core import (
    DeepSeekConfig,
    DeepSeekTranslator,
    MalformedTranslationError,
    MissingApiKeyError,
    NoopTranslator,
    TranslationCacheStore,
    TranslationBlock,
)
import translator_core.deepseek as deepseek_module


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


def test_deepseek_translator_parses_block_aligned_json_response():
    requests = []

    def fake_transport(payload, config):
        requests.append(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"blocks":[{"block_id":"b1","translated_text":"电压源逆变器"}]}'
                    }
                }
            ]
        }

    translator = DeepSeekTranslator(
        DeepSeekConfig(api_key="test-key", model="deepseek-test"),
        transport=fake_transport,
    )

    result = translator.translate_blocks(
        [TranslationBlock(block_id="b1", text="Voltage source inverter")],
        target_lang="zh",
    )

    assert result[0].block_id == "b1"
    assert result[0].source_text == "Voltage source inverter"
    assert result[0].translated_text == "电压源逆变器"
    assert requests[0]["model"] == "deepseek-test"
    assert "Voltage source inverter" in requests[0]["messages"][1]["content"]
    assert "block_id" in requests[0]["messages"][1]["content"]


def test_deepseek_translator_rejects_missing_block_ids():
    def fake_transport(_payload, _config):
        return {
            "choices": [
                {"message": {"content": '{"blocks":[{"block_id":"other","translated_text":"x"}]}'}}
            ]
        }

    translator = DeepSeekTranslator(
        DeepSeekConfig(api_key="test-key"),
        transport=fake_transport,
    )

    with pytest.raises(MalformedTranslationError):
        translator.translate_blocks(
            [TranslationBlock(block_id="b1", text="Voltage source inverter")],
            target_lang="zh",
        )


def test_deepseek_http_transport_sends_json_accept_and_user_agent(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"blocks\\":[]}"}}]}'

    def fake_urlopen(http_request, timeout):
        captured["headers"] = dict(http_request.header_items())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(deepseek_module.request, "urlopen", fake_urlopen)

    deepseek_module._http_transport(
        {"messages": [], "model": "deepseek-test"},
        DeepSeekConfig(api_key="test-key", timeout=12),
    )

    assert captured["headers"]["Accept"] == "application/json"
    assert captured["headers"]["User-agent"] == "pdf2md-converter/0.1"
    assert captured["timeout"] == 12


def test_translation_cache_store_round_trips_records(tmp_path):
    cache = TranslationCacheStore(tmp_path / "translation-cache.jsonl")
    block = TranslationBlock(block_id="b1", text="Voltage source inverter")

    cache.write(
        key="noop:zh:abc",
        block=block,
        translated_text="电压源逆变器",
        provider="noop",
        target_lang="zh",
    )

    cached = cache.read("noop:zh:abc")

    assert cached is not None
    assert cached.block_id == "b1"
    assert cached.source_text == "Voltage source inverter"
    assert cached.translated_text == "电压源逆变器"
