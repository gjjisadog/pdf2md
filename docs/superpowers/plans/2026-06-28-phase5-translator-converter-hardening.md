# Phase 5 Translator And Converter Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a testable DeepSeek translation pipeline, resumable cache, terms extraction, bilingual output, and converter diagnostics to the BookMD generator.

**Architecture:** `translator_core` owns provider models, prompt building, cache storage, and DeepSeek response parsing. `apps/converter_desktop/converter` orchestrates provider selection and writes translated BookMD payloads. Tests use mocked transports and never call live network APIs.

**Tech Stack:** Python 3.12, pytest, argparse, pathlib, json/jsonl, urllib from the standard library or injectable transport functions.

**Execution status:** Completed on 2026-06-28. Verified with `python -m pytest` and `python scripts/verify_release.py`.

---

## Task 1: DeepSeek Client Boundary

**Files:**
- Modify: `packages/translator_core/translator_core/models.py`
- Modify: `packages/translator_core/translator_core/deepseek.py`
- Modify: `packages/translator_core/translator_core/__init__.py`
- Modify: `tests/test_translator_core.py`

- [ ] **Step 1: Write failing DeepSeek parser and transport tests**

Add tests for `DeepSeekTranslator` with a fake transport returning JSON content:

```python
def test_deepseek_translator_parses_block_aligned_json(monkeypatch):
    calls = []

    def fake_transport(payload, config):
        calls.append(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"blocks":[{"block_id":"b1","translated_text":"并网逆变器"}]}'
                    }
                }
            ]
        }

    translator = DeepSeekTranslator(
        DeepSeekConfig(api_key="test-key", model="deepseek-v4-flash"),
        transport=fake_transport,
    )

    result = translator.translate_blocks(
        [TranslationBlock(block_id="b1", text="grid inverter")],
        target_lang="zh",
    )

    assert result[0].block_id == "b1"
    assert result[0].translated_text == "并网逆变器"
    assert calls
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_translator_core.py::test_deepseek_translator_parses_block_aligned_json -q
```

Expected: FAIL because `DeepSeekTranslator` does not exist.

- [ ] **Step 3: Implement client boundary**

Add:
- `DeepSeekTranslator`
- prompt builder that returns JSON-only instructions
- injectable `transport(payload, config)`
- response parser for `choices[0].message.content`
- `MalformedTranslationError` for bad JSON or missing block IDs

- [ ] **Step 4: Run translator tests**

Run:

```bash
python -m pytest tests/test_translator_core.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/translator_core tests/test_translator_core.py
git commit -m "feat: add deepseek translation client boundary"
```

## Task 2: Translation Cache Store

**Files:**
- Modify: `packages/translator_core/translator_core/cache.py`
- Modify: `packages/translator_core/translator_core/__init__.py`
- Modify: `tests/test_translator_core.py`

- [ ] **Step 1: Write failing cache store test**

```python
def test_translation_cache_store_reuses_cached_results(tmp_path):
    cache = TranslationCacheStore(tmp_path / "translation-cache.jsonl")
    block = TranslationBlock(block_id="b1", text="grid inverter")
    key = translation_cache_key("deepseek", "zh", block.text)

    cache.write(key, block, translated_text="并网逆变器")

    cached = cache.read(key)
    assert cached is not None
    assert cached.block_id == "b1"
    assert cached.translated_text == "并网逆变器"
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_translator_core.py::test_translation_cache_store_reuses_cached_results -q
```

Expected: FAIL because `TranslationCacheStore` does not exist.

- [ ] **Step 3: Implement JSONL cache**

Add JSONL records with:
- `schema_version`
- `cache_key`
- `block_id`
- `source_text`
- `translated_text`
- `created_at`

- [ ] **Step 4: Run tests**

Run:

```bash
python -m pytest tests/test_translator_core.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/translator_core tests/test_translator_core.py
git commit -m "feat: add translation cache store"
```

## Task 3: Terms Extraction

**Files:**
- Create: `packages/translator_core/translator_core/terms.py`
- Modify: `packages/translator_core/translator_core/__init__.py`
- Create: `tests/test_terms_extraction.py`

- [ ] **Step 1: Write failing term extraction test**

```python
from translator_core import extract_terms


def test_extract_terms_finds_abbreviations_and_technical_phrases():
    terms = extract_terms([
        "The phase-locked loop (PLL) controls the grid inverter.",
        "The proportional integral controller is tuned offline.",
    ])

    assert any(term["abbr"] == "PLL" and term["source"] == "phase-locked loop" for term in terms)
    assert any(term["source"] == "grid inverter" for term in terms)
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_terms_extraction.py -q
```

Expected: FAIL because `extract_terms` does not exist.

- [ ] **Step 3: Implement deterministic extraction**

Implement phrase and abbreviation heuristics without external dependencies. Keep output shape compatible with `terms.json`.

- [ ] **Step 4: Run tests**

Run:

```bash
python -m pytest tests/test_terms_extraction.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/translator_core tests/test_terms_extraction.py
git commit -m "feat: extract technical terms for bookmd"
```

## Task 4: Converter Translation Integration

**Files:**
- Modify: `apps/converter_desktop/converter/builder.py`
- Modify: `apps/converter_desktop/converter/config.py`
- Modify: `apps/converter_desktop/converter/markdown.py`
- Modify: `tests/test_sample_e2e.py`
- Create: `tests/test_converter_translation.py`

- [ ] **Step 1: Write failing mocked translation E2E test**

Create a test that monkeypatches provider selection to return translated text for one English block, then asserts:
- chapter contains `:::bilingual`
- `translation.json` contains aligned translated text
- `source_map.json` contains `translated_text`
- `search_index.json` searches translated text
- `terms.json` contains at least one extracted term

- [ ] **Step 2: Run and verify failure**

Run:

```bash
python -m pytest tests/test_converter_translation.py -q
```

Expected: FAIL until converter writes translated payloads.

- [ ] **Step 3: Implement integration**

Wire:
- provider selection
- optional cache path
- bilingual config
- `terms.json`
- richer `translation.json`
- translated search text

- [ ] **Step 4: Run tests**

Run:

```bash
python -m pytest tests/test_converter_translation.py tests/test_sample_e2e.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/converter_desktop tests packages/translator_core
git commit -m "feat: integrate translation into bookmd conversion"
```

## Task 5: Converter Diagnostics And Documentation

**Files:**
- Modify: `apps/converter_desktop/converter/cli.py`
- Modify: `docs/deepseek_translation.md`
- Modify: `docs/windows_converter_usage.md`
- Modify: `docs/troubleshooting.md`
- Modify: `docs/phase5.md`

- [ ] **Step 1: Add diagnostics tests**

Add tests asserting conversion output includes a summary line and warnings for missing assets where applicable.

- [ ] **Step 2: Implement CLI summary**

Print:
- output path
- chapter count
- block count
- translated block count
- cache hit count
- warning count

- [ ] **Step 3: Update docs**

Document:
- `DEEPSEEK_API_KEY`
- config keys
- cache behavior
- privacy note that text is sent to DeepSeek only when explicitly enabled
- mocked tests versus manual live API verification

- [ ] **Step 4: Run full verification**

Run:

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output /tmp/bookmd-phase5/sample.bookmd --translate false
python -m converter validate /tmp/bookmd-phase5/sample.bookmd
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/converter_desktop docs tests
git commit -m "docs: document phase five translation workflow"
```
