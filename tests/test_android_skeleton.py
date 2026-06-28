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
    asset = Path(
        "apps/reader-android/app/src/main/assets/bookmd-renderer.html"
    ).read_text(encoding="utf-8")

    assert "window.BookMDReader" in asset
    assert "renderMarkdown" in asset
    assert "loadChapter" in asset
