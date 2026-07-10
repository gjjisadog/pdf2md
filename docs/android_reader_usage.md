# Android Reader Usage

The Android app is an MVP skeleton under `apps/reader-android`.

It currently provides:

- Kotlin Android project structure.
- WebView-based reader shell.
- `BookRepository` for unzipping `.bookmd` into app-private files.
- `SourceMapRepository` for reading `source_map.json`.
- `BookShelfActivity`, `TocActivity`, and `ReaderActivity` boundaries.
- `BookImportActivity` and `SearchActivity` boundaries.
- `SearchRepository` for local `search_index.json` queries.
- Scrollable search results for long result lists on phone-height screens.
- Scrollable shelf and settings screens for long local book lists and compact phones.
- Shelf rows can either resume the last-read chapter or open the book TOC directly.
- `ReadingProgressStore` for local reading progress.
- `BookMdWebBridge` for block/image callbacks from WebView.
- `SourceMapDialog` for first-pass source text display.
- `ReaderSettings` for font size, line height, theme, layout, and language mode defaults.
- Reader toolbar controls for TOC, search, settings, and previous/next chapter navigation, with edge buttons disabled at the first or last chapter.
- CSS-column paged reading with left/right swipe page turns, page count display, and scroll fallback.
- Renderer assets loaded through `file:///android_asset/bookmd-renderer.html`.
- `SettingsActivity` for font size, line height, theme, layout, and language mode.
- `ImageViewerActivity` for full-screen figure/table asset viewing.

The Android renderer assets are copied from `packages/markdown_renderer/renderer`.
After changing renderer HTML/CSS/JS, sync Android assets with:

```bash
python scripts/sync_android_renderer_assets.py
```

The repository test suite verifies the Android project structure, renderer parity, reader boundaries, paged progress persistence, and renderer pagination hooks. APK compilation should be verified with Gradle/Android SDK tooling.

True native pagination remains future work; the current reader uses a WebView/CSS-column paging layer. PDF bbox screenshot tracing is represented by the source-page PDF viewer and bbox overlay.

## Build

The project includes a Gradle wrapper:

```bash
cd apps/reader-android
ANDROID_HOME=/path/to/android-sdk ANDROID_SDK_ROOT=/path/to/android-sdk ./gradlew assembleDebug
```

The debug APK is written to:

```text
apps/reader-android/app/build/outputs/apk/debug/app-debug.apk
```

Phase 4 verified `assembleDebug` successfully with Android SDK 33. A connected device or emulator is required for `adb install`.
Phase 6 release verification runs `assembleDebug` automatically when `ANDROID_HOME` or `ANDROID_SDK_ROOT` is available.

## Emulator Smoke Test

```bash
adb install -r apps/reader-android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.bookmd.reader/.BookShelfActivity
```

After building the APK, a connected device or emulator can run the repeatable smoke helper:

```bash
python scripts/verify_android_reader.py --device-smoke --bookmd path/to/sample.bookmd --search-term SVPWM
```

This helper requires `adb devices` to show at least one `device` entry. If no Android device or emulator is connected, it fails fast instead of waiting indefinitely.

To verify reading progress persistence and cold restore, run:

```bash
python scripts/verify_android_reader.py --device-smoke --bookmd path/to/sample.bookmd --verify-progress
```

This saves progress from the reader, force-stops the app, reopens the shelf, and confirms tapping the book returns directly to the reader WebView.

To exercise the real Android file picker import path, push the sample to the emulator Downloads folder and select it through DocumentsUI with:

```bash
python scripts/verify_android_reader.py --device-smoke --bookmd path/to/sample.bookmd --import-via-picker
```

The default smoke path preloads the book into app-private storage for stability. `--import-via-picker` verifies the user-facing import flow before continuing through shelf -> reader -> source-map -> PDF page checks.

To verify corrupt `.bookmd` handling, run the same device smoke with:

```bash
python scripts/verify_android_reader.py --device-smoke --bookmd path/to/sample.bookmd --import-via-picker --verify-bad-import
```

This first imports a valid sample, then selects a deliberately corrupt `CorruptBookmdSmoke.bookmd` through DocumentsUI and checks that the import screen shows `Import failed:` while the existing shelf book remains available.

To verify a real visual fallback asset opens in the Android media viewer, use a `.bookmd` that contains referenced `assets/generated/...` media and add `--verify-visual-asset`:

```bash
python scripts/verify_android_reader.py --device-smoke --bookmd path/to/visual.bookmd --verify-visual-asset
```

For the current DC-DC real-book artifact, the concrete command is:

```bash
ANDROID_HOME=/opt/homebrew/share/android-commandlinetools \
ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools \
PATH=/opt/homebrew/share/android-commandlinetools/platform-tools:$PATH \
PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_android_reader.py \
  --device-smoke \
  --bookmd tmp/real_book_full_clean_text_visual.bookmd \
  --verify-visual-asset \
  --search-term DC-DC \
  --artifacts-dir tmp/android_reader_verify_visual_asset
```

The helper reads the `.bookmd`, selects the first referenced non-cover visual asset, launches `ImageViewerActivity` with that real app-private asset URI, verifies the viewer WebView opens, and returns to the reader before continuing the normal source-map smoke.

To record a coarse performance baseline for a large `.bookmd`, add `--performance-baseline`:

```bash
python scripts/verify_android_reader.py --device-smoke --bookmd path/to/large.bookmd --search-term voltage --performance-baseline --artifacts-dir tmp/android_reader_perf
```

The helper writes `performance_baseline.json` under the artifacts directory with setup/shelf readiness, open-to-reader, optional search flow, source trace, and total smoke timings. Treat these numbers as a device-specific baseline, not a universal pass/fail threshold.

Current observed large-book baseline on the `BookMdApi33` emulator is:

- open-to-reader: about 4.2 seconds
- progress restore: about 6.5 seconds
- settings round trip: about 6.8 seconds
- search flow: about 12.1 seconds
- source trace: about 4.3 seconds

Use conservative warning thresholds while benchmark coverage is still expanding: warn above 8 seconds for open-to-reader, 10 seconds for progress restore, 10 seconds for settings round trip, 18 seconds for search flow, and 8 seconds for source trace. Do not hard-fail release verification on these thresholds until at least three representative `.bookmd` samples have benchmark data.

For local smoke testing, a sample `.bookmd` can be imported through the file picker or unpacked into app-private storage. Verify shelf -> TOC -> reader, paged left/right swipe, layout switch to scroll, search jump, source-map dialog, settings, progress restore, and image/table viewer.
