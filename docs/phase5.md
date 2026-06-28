# Phase 5 Scope

Phase 5 hardens the Windows converter and translation pipeline so `.bookmd` generation can support real professional translation while remaining local-first, resumable, and testable.

## Positioning

The original prompt listed `translator-core` earlier, but this repository prioritized the package, converter, renderer, and Android reading loop first. After phase four, the largest remaining product gap is translation quality and converter robustness.

## Goals

- Implement a mockable DeepSeek translation client boundary.
- Parse JSON translation responses into block-aligned results.
- Preserve Markdown structure, formulas, variables, units, figure/table numbers, and block IDs.
- Add translation cache storage for resumable conversion.
- Generate useful `terms.json` from OCR/translation inputs.
- Write richer `translation.json` with provider, model, status, cache key, source, translated text, and error fields.
- Support bilingual Markdown output when configured.
- Improve converter diagnostics for Windows usage:
  - clear conversion summary
  - warnings for missing assets
  - config validation
  - paths with spaces and Chinese characters
  - safe behavior for large books

## Non-Goals

- No OCR/Paddle deployment.
- No live API call in automated tests.
- No cloud upload of PDFs.
- No GUI/Web UI yet.
- No machine translation quality benchmarking beyond structure/alignment checks.

## Implementation Plan

1. DeepSeek Client Boundary
   - Add request/response models and prompt builder in `translator_core`.
   - Make the HTTP transport injectable so tests do not call the network.
   - Support timeout, retry, temperature, max_tokens, and model from config/env.

2. Translation Cache
   - Add JSONL cache store with schema version, provider, target language, text hash, source text, translated text, and timestamp.
   - Reuse cached results before calling provider.
   - Keep cache path configurable.

3. Block Alignment And Safety
   - Translate only text-bearing blocks.
   - Skip or protect formulas, code, asset paths, numbers, units, and figure/table labels.
   - Fail clearly if provider output misses a block ID or returns malformed JSON.

4. Terms Extraction
   - Add deterministic heuristic term extraction for common English technical terms and abbreviations.
   - Write `terms.json` with source, target, abbreviation, category, and note fields.

5. Converter Integration
   - Wire provider selection into `build_bookmd`.
   - Generate bilingual Markdown when `translation.bilingual: true`.
   - Fill `translation.json`, `source_map.json.translated_text`, and `search_index.json` from translated text.
   - Emit conversion summary and warnings.

6. Tests And Docs
   - Add mocked DeepSeek tests.
   - Add cache/resume tests.
   - Add converter E2E test for translated/bilingual output.
   - Update `docs/deepseek_translation.md`, `docs/windows_converter_usage.md`, and troubleshooting.

## Acceptance Criteria

- `python -m pytest` passes.
- DeepSeek client is fully testable without network.
- Missing API key still fails clearly for `--translate true --provider deepseek`.
- Mocked DeepSeek translation creates:
  - translated chapter text
  - `terms.json`
  - block-aligned `translation.json`
  - translated `source_map.json`
  - searchable translated text in `search_index.json`
- Re-running conversion with cache avoids duplicate provider calls.
- No formula/image/table custom block syntax is corrupted by translation.

## Completion Record

Completed on 2026-06-28.

Implemented:

- Mockable `DeepSeekTranslator` with strict JSON response parsing and `MalformedTranslationError`.
- JSONL `TranslationCacheStore` with schema version, provider, target language, source text, translated text, cache key, and timestamp.
- Deterministic `extract_terms` for common power-electronics/control terms and abbreviations.
- Converter provider selection, cache reuse, bilingual Markdown, `terms.json`, richer `translation.json`, translated `source_map.json`, translated `search_index.json`, and CLI conversion summary.

Verification:

```bash
python -m pytest
```

Result: 49 passed.
