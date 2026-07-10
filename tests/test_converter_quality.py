import json
import zipfile
from pathlib import Path

from bookmd_core import package_directory
from converter.quality import inspect_bookmd, render_quality_report_markdown


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_bookmd(
    tmp_path: Path,
    *,
    include_original_pdf: bool = True,
    broken_asset: bool = False,
    translation_payload: dict | None = None,
    terms_payload: dict | None = None,
) -> Path:
    root = tmp_path / "book"
    (root / "chapters").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "source").mkdir()
    (root / "assets" / "figure.png").write_bytes(b"png")
    if include_original_pdf:
        (root / "source" / "original.pdf").write_bytes(b"%PDF-1.4\n")
    asset_target = "../assets/missing.png" if broken_asset else "../assets/figure.png"
    (root / "chapters" / "001.md").write_text(
        "\n".join(
            [
                "<!-- block_id: h1; page: 1; bbox: [0, 0, 10, 10] -->",
                "# Chapter 1",
                "",
                f"![Figure]({asset_target})",
            ]
        ),
        encoding="utf-8",
    )
    (root / "chapters" / "002.md").write_text("", encoding="utf-8")
    _write_json(
        root / "book.json",
        {
            "book_id": "book",
            "title": "Power Electronics",
            "chapters": [
                {"id": "ch1", "title": "Chapter 1", "path": "chapters/001.md", "order": 1},
                {"id": "ch2", "title": "Empty", "path": "chapters/002.md", "order": 2},
            ],
        },
    )
    _write_json(
        root / "source_map.json",
        {
            "blocks": [
                {
                    "block_id": "h1",
                    "source_page": 1,
                    "bbox": [0, 0, 10, 10],
                    "source_text": "Chapter 1",
                    "chapter_path": "chapters/001.md",
                }
            ]
        },
    )
    _write_json(root / "terms.json", terms_payload or {"terms": []})
    _write_json(root / "translation.json", translation_payload or {"items": []})
    _write_json(root / "reading_config.json", {"layout": "paged"})
    _write_json(
        root / "search_index.json",
        {
            "items": [
                {
                    "block_id": "h1",
                    "chapter_id": "ch1",
                    "chapter_path": "chapters/001.md",
                    "chapter_title": "Chapter 1",
                    "text": "Chapter 1",
                }
            ]
        },
    )
    return package_directory(root, tmp_path / "book.bookmd")


def test_quality_report_counts_bookmd_structure_and_warnings(tmp_path):
    bookmd = _make_bookmd(tmp_path, broken_asset=True)

    report = inspect_bookmd(bookmd)

    assert report.path == str(bookmd)
    assert report.valid is True
    assert report.title == "Power Electronics"
    assert report.chapter_count == 2
    assert report.empty_chapter_count == 1
    assert report.search_item_count == 1
    assert report.source_map_block_count == 1
    assert report.has_original_pdf is True
    assert report.asset_count == 1
    assert report.broken_asset_references == ["../assets/missing.png"]
    assert "empty chapters: 1" in report.warnings
    assert "broken asset references: 1" in report.warnings


def test_quality_report_warns_when_original_pdf_is_missing(tmp_path):
    bookmd = _make_bookmd(tmp_path, include_original_pdf=False)

    report = inspect_bookmd(bookmd)

    assert report.has_original_pdf is False
    assert "source/original.pdf is missing" in report.warnings


def test_quality_report_renders_markdown_summary(tmp_path):
    bookmd = _make_bookmd(tmp_path)
    report = inspect_bookmd(bookmd)

    markdown = render_quality_report_markdown(report)

    assert "# BookMD Quality Report" in markdown
    assert "- Title: Power Electronics" in markdown
    assert "- Chapters: 2" in markdown
    assert "- Search items: 1" in markdown
    assert "- Source-map blocks: 1" in markdown


def test_quality_report_measures_translation_alignment_and_risks(tmp_path):
    bookmd = _make_bookmd(
        tmp_path,
        translation_payload={
            "provider": "deepseek",
            "model": "deepseek-test",
            "target_lang": "zh",
            "blocks": [
                {
                    "block_id": "h1",
                    "source_text": "The grid inverter uses pulse width modulation.",
                    "translated_text": "并网逆变器 uses pulse width modulation.",
                    "status": "translated",
                },
                {
                    "block_id": "p2",
                    "source_text": "Voltage source inverter.",
                    "translated_text": "",
                    "status": "source",
                },
                {
                    "block_id": "p3",
                    "source_text": "Markdown formula $$G_i(s)$$ must survive.",
                    "translated_text": "公式 $$G_i(s) 必须保留。",
                    "status": "translated",
                },
                {
                    "block_id": "p4",
                    "source_text": "Short source.",
                    "translated_text": "非常长的译文" * 40,
                    "status": "translated",
                },
            ],
        },
        terms_payload={
            "terms": [
                {"source": "grid inverter", "target": "并网逆变器"},
                {"source": "pulse width modulation", "target": "脉宽调制"},
            ]
        },
    )

    report = inspect_bookmd(bookmd)

    assert report.translation_provider == "deepseek"
    assert report.translation_block_count == 4
    assert report.translated_block_count == 3
    assert report.untranslated_block_count == 1
    assert report.translation_coverage_ratio == 0.75
    assert report.untranslated_block_ids == ["p2"]
    assert report.glossary_term_count == 2
    assert report.missing_glossary_targets == ["pulse width modulation -> 脉宽调制"]
    assert report.markdown_risk_block_ids == ["p3"]
    assert report.overlong_translation_block_ids == ["p4"]
    assert "untranslated blocks: 1" in report.warnings
    assert "glossary targets missing: 1" in report.warnings
    assert "translation markdown risks: 1" in report.warnings
    assert "overlong translations: 1" in report.warnings


def test_quality_report_does_not_warn_for_source_only_translation_payload(tmp_path):
    bookmd = _make_bookmd(
        tmp_path,
        translation_payload={
            "provider": "",
            "target_lang": "zh",
            "blocks": [
                {
                    "block_id": "h1",
                    "source_text": "Chapter 1",
                    "translated_text": "",
                    "status": "source",
                }
            ],
        },
    )

    report = inspect_bookmd(bookmd)

    assert report.translation_provider == ""
    assert report.translation_block_count == 0
    assert report.untranslated_block_count == 0
    assert "untranslated blocks: 1" not in report.warnings
