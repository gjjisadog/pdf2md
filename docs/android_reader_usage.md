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
- `ReadingProgressStore` for local reading progress.
- `BookMdWebBridge` for block/image callbacks from WebView.
- `SourceMapDialog` for first-pass source text display.
- `ReaderSettings` for font size, line height, theme, layout, and language mode defaults.
- Renderer assets loaded through `file:///android_asset/bookmd-renderer.html`.
- `SettingsActivity` for font size, line height, theme, layout, and language mode.
- `ImageViewerActivity` for full-screen figure/table asset viewing.

The Android renderer assets are copied from `packages/markdown_renderer/renderer`.
After changing renderer HTML/CSS/JS, sync Android assets with:

```bash
python scripts/sync_android_renderer_assets.py
```

The repository test suite verifies the Android project structure, renderer parity, and reader boundaries. APK compilation should be verified with Gradle/Android SDK tooling.

True native pagination and PDF bbox screenshot tracing remain future work.

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

## Emulator Smoke Test

```bash
adb install -r apps/reader-android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.bookmd.reader/.BookShelfActivity
```

For local smoke testing, a sample `.bookmd` can be imported through the file picker or unpacked into app-private storage. Verify shelf -> TOC -> reader, search jump, source-map dialog, settings, progress restore, and image/table viewer.
