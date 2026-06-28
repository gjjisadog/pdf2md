# Android Reader Usage

The Android app is an MVP skeleton under `apps/reader-android`.

It currently provides:

- Kotlin Android project structure.
- WebView-based reader shell.
- `BookRepository` for unzipping `.bookmd` into app-private files.
- `SourceMapRepository` for reading `source_map.json`.
- Renderer asset placeholder loaded through `file:///android_asset/bookmd-renderer.html`.

Full bookshelf UI, file picker, pagination, and polished reading controls are next-stage work.
