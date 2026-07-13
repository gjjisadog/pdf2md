# Release Checklist

Use this checklist before treating the personal MVP as a releasable local build.

## Automated

- Python tests: `python -m pytest`
- OCR API adapter tests: `python -m pytest tests/test_ocr_client.py tests/test_converter_ocr_cli.py`
- Release verifier: `python scripts/verify_release.py`
- Sample package: build `samples/ocr_output_sample` into a temporary `.bookmd`
- Package validation: `python -m converter validate path/to/sample.bookmd --strict`
- Wheel isolation: `python -m build --wheel`, install the wheel in a clean environment, then run `bookmd --help`
- Cross-platform visual assets: `python -m pytest tests/test_portable_visuals.py -q` (also required on `windows-latest` CI)
- BookMD benchmark report: `python scripts/run_bookmd_benchmarks.py --manifest docs/bookmd_benchmarks.json --output tmp/bookmd_benchmark_report.json`
- Real-book quality report: `python -m converter quality-report tmp/real_book_full_clean_text_visual.bookmd --format json`
- Renderer parity: `python -m pytest tests/test_renderer_assets.py`
- Android reader verifier: `python scripts/verify_android_reader.py`
- Optional Android device smoke: `python scripts/verify_android_reader.py --device-smoke --bookmd path/to/sample.bookmd --search-term SVPWM` with `adb devices` showing a connected `device`
- Optional Android visual asset smoke: `python scripts/verify_android_reader.py --device-smoke --bookmd tmp/real_book_full_clean_text_visual.bookmd --verify-visual-asset --search-term DC-DC --artifacts-dir tmp/android_reader_verify_visual_asset` with `adb devices` showing a connected `device`
- Android APK: `cd apps/reader-android && sh ./gradlew :app:assembleDebug` when `ANDROID_HOME` is available
- iPadOS Reader: `cd apps/reader-ios && python3 scripts/verify_ios_release.py`

### Android aapt2 preflight

`scripts/verify_android_reader.py` checks installed SDK `aapt2` binaries before invoking Gradle. If every `build-tools/*/aapt2 version` command times out, repair the local Android toolchain before treating Android release verification as valid:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export ANDROID_SDK_ROOT=$ANDROID_HOME
yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --install "platforms;android-33" "build-tools;33.0.2"
"$ANDROID_HOME/build-tools/33.0.2/aapt2" version
```

If macOS still hangs in `aapt2`, Gradle's Maven-provided `aapt2` can fail the same way because the binary never reaches its own startup handshake. Treat repeated timeouts across SDK and Gradle-cache `aapt2` binaries as a local macOS process loader/dyld issue, then run Android verification on a Linux/Docker/CI host with a healthy Android SDK.

## Manual Android Acceptance

- Install `apps/reader-android/app/build/outputs/apk/debug/app-debug.apk`.
- Import/open a `.bookmd` from the file picker.
- Verify shelf, TOC, reader, settings, media viewer, source map dialog, search, and progress restore.
- Confirm the renderer assets are current after any HTML/CSS/JS changes.

## Personal Conversion Gate

Use this sequence for a real personal technical-book conversion after OCR batches are available:

```bash
python -m converter build --source-pdf <source.pdf> --ocr-output <ocr-output-dir> --output <book.bookmd> --translate false --generate-block-assets true
python -m converter validate <book.bookmd> --strict
python -m converter quality-report <book.bookmd> --format json
python scripts/verify_android_reader.py --device-smoke --bookmd <book.bookmd> --verify-visual-asset --search-term <known-term>
```

Manual review before phone import:

- Cover appears as first visual content.
- TOC/chapter list is usable.
- Formula, figure, and table pages preserve original visual information.
- Search finds known technical terms.
- Source-map jump opens the correct PDF page.
- Reading progress restores after app restart.

## Manual iPadOS Acceptance

- Run `cd apps/reader-ios && python3 scripts/verify_ios_release.py`.
- Import `tmp/real_book_full_clean_toc.bookmd` through Files.
- On a physical iPad mini, verify Files picker import, direct finger tap on rendered WKWebView text for source map, settings typography/theme changes, portrait layout, landscape split layout, and late-book responsiveness. The simulator gate already covers shelf, TOC, search jump, rendered block exposure, source-map data, PDF page review, reading settings controls, terms list, progress restore, and rotation.

## Known limitations

- OCR/Paddle deployment is not included.
- DeepSeek live translation is optional and not required in automated tests.
- OCR live API calls are optional and not required in automated tests.
- PDF bbox screenshot tracing is represented by source-map metadata, not native PDF overlay.
- Android reader remains an MVP WebView reader, not a fully native paginated engine.
- Android reader build/test currently depends on a healthy local Android SDK; this machine currently has a local macOS `aapt2` startup hang across installed build-tools.
- iPadOS reader build/test depends on a healthy local Xcode installation and an available iPad mini simulator.
