import json
import argparse
import subprocess
import sys

from bookmd_core import validate_bookmd
from bookmd_core import package_directory
from converter import cli


def test_cli_build_options_can_enable_generated_block_assets():
    options = cli._build_options_from_args(
        argparse.Namespace(
            source_pdf="source.pdf",
            ocr_output="ocr",
            output="out.bookmd",
            translate="false",
            target_lang="zh",
            provider="noop",
            config=None,
            generate_block_assets="true",
        )
    )

    assert options.config["output"]["generate_block_assets"] is True


def test_cli_build_help_documents_generated_block_assets_flag():
    completed = subprocess.run(
        [sys.executable, "-m", "converter", "build", "--help"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "--generate-block-assets" in completed.stdout


def test_cli_quality_report_outputs_json(tmp_path, capsys):
    root = tmp_path / "book"
    (root / "chapters").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "source").mkdir()
    (root / "chapters" / "001.md").write_text("# Intro\n", encoding="utf-8")
    (root / "source" / "original.pdf").write_bytes(b"%PDF-1.4\n")
    (root / "book.json").write_text(
        json.dumps(
            {
                "book_id": "b",
                "title": "Intro Book",
                "chapters": [{"id": "ch1", "title": "Intro", "path": "chapters/001.md"}],
            }
        ),
        encoding="utf-8",
    )
    for name, payload in {
        "source_map.json": {"blocks": []},
        "terms.json": {"terms": []},
        "translation.json": {"items": []},
        "reading_config.json": {},
        "search_index.json": {"items": []},
    }.items():
        (root / name).write_text(json.dumps(payload), encoding="utf-8")
    bookmd = package_directory(root, tmp_path / "intro.bookmd")

    exit_code = cli.main(["quality-report", str(bookmd), "--format", "json"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["title"] == "Intro Book"
    assert output["chapter_count"] == 1
    assert output["has_original_pdf"] is True


def test_cli_quality_report_outputs_markdown(tmp_path, capsys):
    root = tmp_path / "book"
    (root / "chapters").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "source").mkdir()
    (root / "chapters" / "001.md").write_text("# Intro\n", encoding="utf-8")
    (root / "book.json").write_text(
        json.dumps(
            {
                "book_id": "b",
                "title": "Markdown Book",
                "chapters": [{"id": "ch1", "title": "Intro", "path": "chapters/001.md"}],
            }
        ),
        encoding="utf-8",
    )
    for name, payload in {
        "source_map.json": {"blocks": []},
        "terms.json": {"terms": []},
        "translation.json": {"items": []},
        "reading_config.json": {},
        "search_index.json": {"items": []},
    }.items():
        (root / name).write_text(json.dumps(payload), encoding="utf-8")
    bookmd = package_directory(root, tmp_path / "markdown.bookmd")

    exit_code = cli.main(["quality-report", str(bookmd), "--format", "markdown"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "# BookMD Quality Report" in output
    assert "- Title: Markdown Book" in output


def test_cli_build_generates_valid_bookmd(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# 第一章 绪论\n\n内容", encoding="utf-8")
    (sample / "result.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "h1",
                        "page": 1,
                        "type": "heading",
                        "level": 1,
                        "text": "第一章 绪论",
                        "bbox": [0, 0, 10, 10],
                    },
                    {
                        "block_id": "p1",
                        "page": 1,
                        "type": "paragraph",
                        "text": "并网逆变器",
                        "bbox": [0, 10, 10, 20],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    pdf = tmp_path / "original.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% placeholder\n")
    output = tmp_path / "out.bookmd"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "converter",
            "build",
            "--source-pdf",
            str(pdf),
            "--ocr-output",
            str(sample),
            "--output",
            str(output),
            "--translate",
            "false",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert validate_bookmd(output).valid is True


def test_cli_validate_ocr_reports_valid_output(tmp_path, capsys):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("Grid inverter\n", encoding="utf-8")
    (sample / "result.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "p1",
                        "page": 2,
                        "type": "paragraph",
                        "text": "Grid inverter",
                        "bbox": [1, 2, 30, 40],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (sample / "source_map.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "p1",
                        "source_page": 2,
                        "bbox": [1, 2, 30, 40],
                        "source_text": "Grid inverter",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (sample / "parse.log").write_text("ok\n", encoding="utf-8")

    exit_code = cli.main(["validate-ocr", str(sample)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Valid OCR output" in output
    assert "blocks=1" in output
    assert "source_map_blocks=1" in output


def test_cli_validate_ocr_reports_missing_source_map(tmp_path, capsys):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("Grid inverter\n", encoding="utf-8")
    (sample / "result.json").write_text('{"blocks":[]}', encoding="utf-8")
    (sample / "parse.log").write_text("ok\n", encoding="utf-8")

    exit_code = cli.main(["validate-ocr", str(sample)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "ERROR: source_map.json does not exist" in output


def test_cli_validate_ocr_reports_invalid_source_map_page(tmp_path, capsys):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("Grid inverter\n", encoding="utf-8")
    (sample / "result.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "p1",
                        "page": 2,
                        "type": "paragraph",
                        "text": "Grid inverter",
                        "bbox": [1, 2, 30, 40],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (sample / "source_map.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "p1",
                        "source_page": "two",
                        "bbox": [1, 2, 30, 40],
                        "source_text": "Grid inverter",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (sample / "parse.log").write_text("ok\n", encoding="utf-8")

    exit_code = cli.main(["validate-ocr", str(sample)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "ERROR: source_map blocks do not align with OCR blocks" in output


def test_cli_validation_commands_default_to_strict_for_v1(tmp_path, capsys):
    root = tmp_path / "v1"
    (root / "chapters").mkdir(parents=True)
    (root / "book.json").write_text(
        json.dumps(
            {
                "format_version": "1.0",
                "book_id": "book",
                "title": "Invalid v1",
                "author": "",
                "source_pdf": "source.pdf",
                "language": "en",
                "created_at": "2026-07-14T00:00:00+00:00",
                "version": "1.0",
                "chapters": [
                    {"id": "chapter-1", "title": "Chapter", "path": "chapters/001.md", "order": 1}
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "chapters" / "001.md").write_text("# Chapter\n", encoding="utf-8")
    for name in [
        "source_map.json",
        "terms.json",
        "translation.json",
        "reading_config.json",
        "search_index.json",
    ]:
        (root / name).write_text("{}", encoding="utf-8")
    bookmd = package_directory(root, tmp_path / "invalid-v1.bookmd")

    validate_exit = cli.main(["validate", str(bookmd)])
    validate_output = capsys.readouterr().out
    quality_exit = cli.main(["quality-report", str(bookmd), "--format", "json"])
    quality_output = json.loads(capsys.readouterr().out)

    assert validate_exit == 1
    assert "ERROR:" in validate_output
    assert quality_exit == 1
    assert quality_output["valid"] is False
