from pathlib import Path

from converter.builder import BuildOptions, _book_manifest
from converter.chapters import Chapter


def test_builder_emits_bookmd_v1_manifest(tmp_path):
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n")
    manifest = _book_manifest(
        BuildOptions(source_pdf=source_pdf, ocr_output=tmp_path, output=tmp_path / "out.bookmd"),
        {"metadata": {"title": "Fixture"}},
        [Chapter("ch_001", "Chapter One", "chapters/001.md", 1, [])],
    )

    assert manifest["format_version"] == "1.0"
    assert manifest["version"] == "1.0"
