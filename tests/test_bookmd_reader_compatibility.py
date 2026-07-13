from pathlib import Path


def test_android_manifest_model_accepts_legacy_and_v1_format_markers():
    model = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookModels.kt"
    ).read_text(encoding="utf-8")
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "formatVersion: String?" in model
    assert 'optString("format_version").takeIf' in repository


def test_ios_manifest_model_accepts_legacy_and_v1_format_markers():
    model = Path("apps/reader-ios/Sources/BookMDReaderCore/BookModels.swift").read_text(
        encoding="utf-8"
    )

    assert "public let formatVersion: String?" in model
    assert 'case formatVersion = "format_version"' in model
