# Troubleshooting

## `result.json does not exist`

Check that `--ocr-output` points to the directory containing `result.json`.

## `result.md does not exist`

The converter requires both `result.json` and `result.md`, even though MVP mainly uses `result.json`.

## `Source PDF does not exist`

Check `--source-pdf`. Paths with spaces are supported when quoted.

## `OCR_API_URL is required`

Set `OCR_API_URL` before using `python -m converter ocr` or `python -m converter build-from-pdf`. `OCR_API_KEY` is optional for services that do not require bearer auth.

## OCR API response is rejected

The generic OCR adapter expects a JSON object with a `blocks` array. Each block should include text, page, type, and bbox fields when available. Run the OCR command alone first so you can inspect the generated `result.json` before building `.bookmd`.

## Whole PDF OCR job stays `running`

Use batch mode instead of sending the full PDF as one job:

```bash
python -m converter ocr --source-pdf path/to/book.pdf --output-dir path/to/ocr_output --batch-size 1
```

Use `--max-pages 6` for a small smoke test before processing the full book.

Batch splitting uses the portable PDF backend first. If PDFium and the `pypdf` fallback both cannot split the PDF, pre-split the file with a PDF tool and OCR the smaller files separately.

## `DEEPSEEK_API_KEY is required`

Use `--translate false` for the default path, use `--provider noop` for local no-op translation tests, or set `DEEPSEEK_API_KEY` before selecting the DeepSeek provider.

## DeepSeek returned malformed translation JSON

The converter expects a JSON object with one translated entry per input `block_id`. Re-run with `--provider noop` to isolate packaging issues, or retry DeepSeek with a smaller OCR batch in a future batching workflow.

## Translation cache seems stale

Set a new `translation.cache_path` in config or delete the JSONL cache file. Cache keys include provider, target language, and source text hash.

## Invalid `.bookmd`

Run:

```bash
python -m converter validate path/to/book.bookmd
```

The command is strict by default and reports schema errors, unsafe/duplicate ZIP entries, dangling cross-file references, and missing visual assets. Legacy 0.1 packages remain readable and emit a migration warning; use `--compat` only when an older structural check is required.

## Android build tool not found

The MVP repository includes a standard Gradle/Kotlin Android project structure, but this machine may not have `gradle` or an Android SDK installed. Open `apps/reader-android` in Android Studio, or install Gradle/Android SDK tooling before running an APK build.

## Android renderer looks stale

The Android WebView renderer is copied from `packages/markdown_renderer/renderer`.
After editing renderer HTML, CSS, or JS, run:

```bash
python scripts/sync_android_renderer_assets.py
```

Then run `python -m pytest tests/test_renderer_assets.py -q` to verify Android assets still match the package renderer.

## Images or tables do not open full screen

Check that the chapter Markdown asset paths point to `../assets/...` before import. `ReaderActivity` rewrites those paths to app-private `file://` paths when loading a chapter. If the image renders but does not open, check `BookMdWebBridge.onImageSelected` and `ImageViewerActivity`.
