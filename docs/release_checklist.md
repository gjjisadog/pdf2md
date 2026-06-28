# Release Checklist

Use this checklist before treating the personal MVP as a releasable local build.

## Automated

- Python tests: `python -m pytest`
- Release verifier: `python scripts/verify_release.py`
- Sample package: build `samples/ocr_output_sample` into a temporary `.bookmd`
- Package validation: `python -m converter validate path/to/sample.bookmd`
- Renderer parity: `python -m pytest tests/test_renderer_assets.py`
- Android APK: `cd apps/reader-android && ./gradlew assembleDebug` when `ANDROID_HOME` is available

## Manual Android Acceptance

- Install `apps/reader-android/app/build/outputs/apk/debug/app-debug.apk`.
- Import/open a `.bookmd` from the file picker.
- Verify shelf, TOC, reader, settings, media viewer, source map dialog, search, and progress restore.
- Confirm the renderer assets are current after any HTML/CSS/JS changes.

## Known limitations

- OCR/Paddle deployment is not included.
- DeepSeek live translation is optional and not required in automated tests.
- PDF bbox screenshot tracing is represented by source-map metadata, not native PDF overlay.
- Android reader remains an MVP WebView reader, not a fully native paginated engine.
