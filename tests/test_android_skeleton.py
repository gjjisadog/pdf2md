from pathlib import Path


def test_android_reader_skeleton_has_webview_and_repository_boundaries():
    root = Path("apps/reader-android")

    assert (root / "settings.gradle.kts").exists()
    main = (
        root / "app/src/main/java/com/bookmd/reader/MainActivity.kt"
    ).read_text(encoding="utf-8")
    repo = (
        root / "app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "WebView" in main
    assert "BookRepository" in repo
    assert "book.json" in repo


def test_android_reader_declares_first_phase_screen_boundaries():
    root = Path("apps/reader-android")
    manifest = (root / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    java_root = root / "app/src/main/java/com/bookmd/reader"

    assert "BookShelfActivity" in manifest
    assert "TocActivity" in manifest
    assert "ReaderActivity" in manifest
    assert (java_root / "BookShelfActivity.kt").exists()
    assert (java_root / "TocActivity.kt").exists()
    assert (java_root / "ReaderActivity.kt").exists()
    assert (java_root / "settings/ReaderSettings.kt").exists()


def test_android_repository_models_manifest_and_chapters():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    repo = (root / "data/BookRepository.kt").read_text(encoding="utf-8")
    model = (root / "data/BookModels.kt").read_text(encoding="utf-8")

    assert "data class BookManifest" in model
    assert "data class BookChapter" in model
    assert "readManifest" in repo
    assert "readChapterMarkdown" in repo


def test_android_asset_uses_bookmd_renderer_markdown_api():
    root = Path("apps/reader-android/app/src/main/assets")
    html = (root / "bookmd-renderer.html").read_text(encoding="utf-8")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "bookmd-renderer.css" in html
    assert "bookmd-renderer.js" in html
    assert "window.BookMDReader" in js
    assert "renderMarkdown" in js
    assert "loadChapter" in js
    assert "jumpToBlock" in js
    assert "searchInChapter" in js


def test_android_reader_has_phase_two_local_reading_boundaries():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )

    assert "BookImportActivity" in manifest
    assert (root / "BookImportActivity.kt").exists()
    assert (root / "SearchActivity.kt").exists()
    assert (root / "data/SearchRepository.kt").exists()
    assert (root / "data/ReadingProgressStore.kt").exists()
    assert (root / "ui/SourceMapDialog.kt").exists()


def test_android_reader_wires_webview_bridge_for_source_and_images():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")

    assert "addJavascriptInterface" in reader
    assert "AndroidBookMD" in reader
    assert "onBlockSelected" in bridge
    assert "onImageSelected" in bridge
    assert "SourceMapDialog" in bridge


def test_android_source_map_repository_can_find_block():
    source_map = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SourceMapRepository.kt"
    ).read_text(encoding="utf-8")

    assert "findBlock" in source_map
    assert "block_id" in source_map
    assert "source_text" in source_map


def test_android_import_shelf_toc_reader_flow_is_wired():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    importer = (root / "BookImportActivity.kt").read_text(encoding="utf-8")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")
    toc = (root / "TocActivity.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")

    assert "Intent.ACTION_OPEN_DOCUMENT" in importer
    assert "onActivityResult" in importer
    assert "importBook" in importer
    assert "listBooks" in shelf
    assert "TocActivity" in shelf
    assert "readManifest" in toc
    assert "ReaderActivity" in toc
    assert "loadChapter" in reader
    assert "readChapterMarkdown" in reader
    assert "rewriteAssetPaths" in reader
    assert "jumpToBlock" in reader


def test_android_search_flow_jumps_to_reader_block():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    search = (root / "SearchActivity.kt").read_text(encoding="utf-8")
    repository = (root / "data/SearchRepository.kt").read_text(encoding="utf-8")

    assert "SearchRepository" in search
    assert "ReaderActivity" in search
    assert "target_block_id" in search
    assert "search_index.json" in repository
    assert "chapter_path" in repository


def test_android_source_map_dialog_shows_page_bbox_and_text():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    source_map = (root / "data/SourceMapRepository.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")

    assert "bbox" in source_map
    assert "sourcePage" in source_map
    assert "sourceText" in source_map
    assert "findBlock" in bridge
    assert "sourcePage" in bridge
    assert "bbox" in bridge


def test_android_reader_has_settings_screen_and_modes():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    settings = (root / "settings/ReaderSettings.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")

    assert "SettingsActivity" in manifest
    assert (root / "SettingsActivity.kt").exists()
    assert "fontSize" in settings
    assert "lineHeight" in settings
    assert "theme" in settings
    assert "layout" in settings
    assert "languageMode" in settings
    assert "reading_config.json" in reader


def test_android_reader_has_image_viewer_for_media_taps():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")
    viewer = (root / "ImageViewerActivity.kt").read_text(encoding="utf-8")

    assert "ImageViewerActivity" in manifest
    assert (root / "ImageViewerActivity.kt").exists()
    assert "onImageSelected" in bridge
    assert "EXTRA_MEDIA_URI" in bridge or "media_uri" in bridge
    assert "WebView" in viewer
    assert "loadDataWithBaseURL" in viewer


def test_android_reader_persists_reading_progress():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    progress = (root / "data/ReadingProgressStore.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")
    js = Path(
        "packages/markdown_renderer/renderer/bookmd-renderer.js"
    ).read_text(encoding="utf-8")

    assert "saveProgress" in progress
    assert "readProgress" in progress
    assert "currentProgress" in js
    assert "restoreProgress" in js
    assert "ReadingProgressStore" in reader
