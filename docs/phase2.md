# Phase 2 Scope

Phase 2 turns the first-phase skeleton into a local reading loop that can be tried with sample `.bookmd` files.

## Completed In Phase 2

- Converter reads a small `config.yaml` subset through `--config`.
- Converter can skip embedding `source/original.pdf` when `output.save_original_pdf: false`.
- Converter writes metadata title/author from OCR `metadata`.
- `.bookmd` packaging uses deterministic zip entries.
- Renderer supports Markdown loading, custom block rendering, source-map click callbacks, image callbacks, chapter block jumping, and in-chapter search highlighting.
- Android skeleton adds import, shelf, table-of-contents, reader, search, progress, WebView bridge, and source-map dialog boundaries.

## Verification

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
```

Android APK compilation still requires Gradle and Android SDK tooling on the target machine.
