# Windows Converter Usage

Run from the repository root.

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
```

With config:

```bash
python -m converter build \
  --source-pdf samples/ocr_output_sample/original.pdf \
  --ocr-output samples/ocr_output_sample \
  --output samples/bookmd_sample/sample.bookmd \
  --config config.yaml
```

Supported MVP config keys:

```yaml
translation:
  default_target_lang: zh
  bilingual: true
  cache: true
  cache_path: .cache/bookmd-translation-cache.jsonl
output:
  save_original_pdf: true
reading:
  layout: paged
  theme: light
  font_size: 18
  line_height: 1.75
```

Required OCR output:

```text
ocr_output/
  result.md
  result.json
  assets/
```

The converter does not run OCR and does not install Paddle-related tooling.

No-op translation smoke test:

```bash
python -m converter build \
  --source-pdf samples/ocr_output_sample/original.pdf \
  --ocr-output samples/ocr_output_sample \
  --output samples/bookmd_sample/sample.bookmd \
  --translate true \
  --provider noop \
  --config config.yaml
```

DeepSeek translation requires environment variables documented in `docs/deepseek_translation.md`.
The command prints a conversion summary with chapter, block, translated block, and warning counts.
