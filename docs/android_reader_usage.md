# Android Reader Usage

The Android app is an MVP skeleton under `apps/reader-android`.

It currently provides:

- Kotlin Android project structure.
- WebView-based reader shell.
- `BookRepository` for unzipping `.bookmd` into app-private files.
- `SourceMapRepository` for reading `source_map.json`.
- `BookShelfActivity`, `TocActivity`, and `ReaderActivity` boundaries.
- `ReaderSettings` for font size, line height, theme, layout, and language mode defaults.
- Renderer asset placeholder loaded through `file:///android_asset/bookmd-renderer.html`.

The repository test suite verifies the Android project structure and reader boundaries. APK compilation should be verified in Android Studio or a machine with Gradle/Android SDK tooling available.

Full file picker, true pagination, and polished reading controls are next-stage work.
