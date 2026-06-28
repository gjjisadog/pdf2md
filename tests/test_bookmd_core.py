import json
import zipfile

from bookmd_core import REQUIRED_FILES, validate_bookmd


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
