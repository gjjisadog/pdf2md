import json
import zipfile

from bookmd_core import REQUIRED_FILES, read_book_manifest, validate_bookmd


def test_validate_bookmd_accepts_required_files(tmp_path):
    archive = tmp_path / "sample.bookmd"
    with zipfile.ZipFile(archive, "w") as zf:
        for name in REQUIRED_FILES:
            payload = {"chapters": []} if name == "book.json" else {}
            zf.writestr(name, json.dumps(payload))
        zf.writestr("chapters/001_intro.md", "# Intro")

    result = validate_bookmd(archive)

    assert result.valid is True
    assert result.errors == []


def test_validate_bookmd_reports_missing_manifest(tmp_path):
    archive = tmp_path / "broken.bookmd"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("source_map.json", "{}")

    result = validate_bookmd(archive)

    assert result.valid is False
    assert "book.json" in result.errors[0]


def test_read_book_manifest_returns_json_payload(tmp_path):
    archive = tmp_path / "sample.bookmd"
    manifest = {
        "book_id": "book-1",
        "title": "Control Systems",
        "chapters": [{"id": "ch_001", "title": "Intro", "path": "chapters/001.md"}],
    }
    with zipfile.ZipFile(archive, "w") as zf:
        for name in REQUIRED_FILES:
            zf.writestr(name, json.dumps(manifest if name == "book.json" else {}))
        zf.writestr("chapters/001.md", "# Intro")
        zf.writestr("source/original.pdf", "%PDF-1.4")

    payload = read_book_manifest(archive)

    assert payload["title"] == "Control Systems"
    assert payload["chapters"][0]["path"] == "chapters/001.md"


def test_validate_bookmd_requires_manifest_chapter_files(tmp_path):
    archive = tmp_path / "broken.bookmd"
    manifest = {
        "book_id": "book-1",
        "title": "Broken",
        "chapters": [{"id": "ch_001", "title": "Missing", "path": "chapters/missing.md"}],
    }
    with zipfile.ZipFile(archive, "w") as zf:
        for name in REQUIRED_FILES:
            zf.writestr(name, json.dumps(manifest if name == "book.json" else {}))
        zf.writestr("chapters/001.md", "# Intro")

    result = validate_bookmd(archive)

    assert result.valid is False
    assert any("chapters/missing.md" in error for error in result.errors)
