# DeepSeek Translation

The converter can run without translation, with a local no-op provider, or through the DeepSeek-compatible client boundary.

Default behavior:

- `--translate false` is the default path.
- `NoopTranslator` preserves block alignment and returns source text.
- `DeepSeekTranslator` is mockable and covered by tests without live network calls.

Required environment for live DeepSeek calls:

```bash
export DEEPSEEK_API_KEY=sk-...
export DEEPSEEK_MODEL=deepseek-v4-flash
export DEEPSEEK_TIMEOUT=60
export DEEPSEEK_RETRY=3
export DEEPSEEK_TEMPERATURE=0.2
export DEEPSEEK_MAX_TOKENS=4096
```

Optional:

```bash
export DEEPSEEK_BASE_URL=https://api.deepseek.com/chat/completions
```

The prompt asks the model to return JSON only, preserve every `block_id`, and avoid changing formulas, variables, units, figure/table numbers, Markdown links, and code. Malformed JSON or missing block IDs fail the conversion clearly instead of silently corrupting alignment.

Example config:

```yaml
translation:
  default_target_lang: zh
  bilingual: true
  cache: true
  cache_path: .cache/bookmd-translation-cache.jsonl
```

The cache is JSONL and stores source text, translated text, provider, target language, cache key, and timestamp. Re-running the same conversion with the same `cache_path` reuses cached blocks before calling the provider.

After building a translated `.bookmd`, run:

```bash
python -m converter quality-report path/to/book.bookmd --format json
```

For translation review, check `translation_provider`, `translation_coverage_ratio`, `untranslated_block_ids`, `missing_glossary_targets`, `markdown_risk_block_ids`, and `overlong_translation_block_ids`. A live DeepSeek pilot should have high coverage, no missing glossary targets for reviewed terms, and no Markdown risk warnings before importing to a reader.

privacy notes:

- With `--translate false` or `--provider noop`, no text is sent to a remote service.
- With `--provider deepseek`, OCR block text is sent to the configured DeepSeek-compatible endpoint.
- The converter does not upload the source PDF file.
- Keep `DEEPSEEK_API_KEY` out of committed config files and shell history when possible.
