import json
from pathlib import Path

from bookmd_core import package_directory
from scripts.run_bookmd_benchmarks import run_benchmarks


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_bookmd(tmp_path: Path) -> Path:
    root = tmp_path / "book"
    (root / "chapters").mkdir(parents=True)
    (root / "assets" / "cover").mkdir(parents=True)
    (root / "source").mkdir()
    (root / "assets" / "cover" / "page_001.png").write_bytes(b"png")
    (root / "source" / "original.pdf").write_bytes(b"%PDF-1.4\n")
    (root / "chapters" / "001.md").write_text(
        "\n".join(
            [
                "<!-- block_id: p1; page: 1; bbox: [0, 0, 10, 10] -->",
                "# Chapter 1",
                "",
                "![Cover](../assets/cover/page_001.png)",
            ]
        ),
        encoding="utf-8",
    )
    _write_json(
        root / "book.json",
        {
            "book_id": "book",
            "title": "Benchmark Book",
            "chapters": [
                {"id": "ch1", "title": "Chapter 1", "path": "chapters/001.md", "order": 1},
            ],
        },
    )
    _write_json(
        root / "source_map.json",
        {
            "blocks": [
                {
                    "block_id": "p1",
                    "source_page": 1,
                    "bbox": [0, 0, 10, 10],
                    "source_text": "Chapter 1",
                    "chapter_path": "chapters/001.md",
                }
            ]
        },
    )
    _write_json(root / "terms.json", {"terms": []})
    _write_json(root / "translation.json", {"items": []})
    _write_json(root / "reading_config.json", {"layout": "paged"})
    _write_json(
        root / "search_index.json",
        {
            "items": [
                {
                    "block_id": "p1",
                    "chapter_id": "ch1",
                    "chapter_path": "chapters/001.md",
                    "chapter_title": "Chapter 1",
                    "text": "Chapter 1",
                }
            ]
        },
    )
    return package_directory(root, tmp_path / "book.bookmd")


def test_benchmark_runner_reports_ready_and_pending_samples(tmp_path):
    bookmd = _make_bookmd(tmp_path)
    manifest = tmp_path / "benchmarks.json"
    output = tmp_path / "report.json"
    _write_json(
        manifest,
        {
            "schema": "bookmd_benchmark_manifest_v1",
            "samples": [
                {
                    "id": "ready_book",
                    "label": "Ready Book",
                    "document_type": "technical_book",
                    "status": "ready",
                    "bookmd": str(bookmd),
                    "notes": "fixture",
                },
                {
                    "id": "pending_scan",
                    "label": "Pending Scan",
                    "document_type": "scanned_low_quality_pdf",
                    "status": "pending",
                    "bookmd": str(tmp_path / "missing.bookmd"),
                    "notes": "not selected yet",
                },
            ],
        },
    )

    exit_code = run_benchmarks(manifest, output)

    report = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report["schema"] == "bookmd_benchmark_report_v1"
    assert report["summary"] == {
        "sample_count": 2,
        "measured_count": 1,
        "pending_count": 1,
        "missing_count": 0,
        "invalid_count": 0,
    }
    ready, pending = report["samples"]
    assert ready["id"] == "ready_book"
    assert ready["status"] == "measured"
    assert ready["valid"] is True
    assert ready["title"] == "Benchmark Book"
    assert ready["chapter_count"] == 1
    assert ready["search_item_count"] == 1
    assert ready["source_map_block_count"] == 1
    assert ready["has_cover"] is True
    assert ready["asset_count"] == 1
    assert ready["referenced_asset_count"] == 1
    assert pending["id"] == "pending_scan"
    assert pending["status"] == "pending"
    assert pending["valid"] is None


def test_benchmark_runner_fails_strict_mode_when_ready_sample_is_missing(tmp_path):
    manifest = tmp_path / "benchmarks.json"
    output = tmp_path / "report.json"
    _write_json(
        manifest,
        {
            "schema": "bookmd_benchmark_manifest_v1",
            "samples": [
                {
                    "id": "missing_ready",
                    "label": "Missing Ready",
                    "document_type": "technical_book",
                    "status": "ready",
                    "bookmd": str(tmp_path / "missing.bookmd"),
                    "notes": "should fail strict mode",
                }
            ],
        },
    )

    exit_code = run_benchmarks(manifest, output, require_ready=True)

    report = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert report["summary"]["missing_count"] == 1
    assert report["samples"][0]["status"] == "missing"
    assert report["samples"][0]["errors"] == ["ready benchmark artifact is missing"]
