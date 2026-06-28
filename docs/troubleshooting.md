# Troubleshooting

## `result.json does not exist`

Check that `--ocr-output` points to the directory containing `result.json`.

## `result.md does not exist`

The converter requires both `result.json` and `result.md`, even though MVP mainly uses `result.json`.

## `Source PDF does not exist`

Check `--source-pdf`. Paths with spaces are supported when quoted.

## `DEEPSEEK_API_KEY is required`

Use `--translate false` for the MVP default path, or set `DEEPSEEK_API_KEY` before selecting the DeepSeek provider.

## Invalid `.bookmd`

Run:

```bash
python -m converter validate path/to/book.bookmd
```

The command reports missing required files.

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
