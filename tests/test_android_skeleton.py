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
