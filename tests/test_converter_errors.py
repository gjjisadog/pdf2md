import json
import subprocess
import sys


def run_converter(*args):
    return subprocess.run(
        [sys.executable, "-m", "converter", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def make_minimal_ocr_dir(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# Intro", encoding="utf-8")
    (sample / "result.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "p1",
                        "page": 1,
                        "type": "paragraph",
                        "bbox": [0, 0, 1, 1],
                        "text": "text",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return sample


def test_cli_reports_missing_result_json(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# Intro", encoding="utf-8")
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    completed = run_converter(
        "build",
        "--source-pdf",
        str(pdf),
        "--ocr-output",
        str(sample),
        "--output",
        str(tmp_path / "out.bookmd"),
    )

    assert completed.returncode == 1
    assert "result.json does not exist" in completed.stdout


def test_cli_reports_missing_source_pdf(tmp_path):
    sample = make_minimal_ocr_dir(tmp_path)

    completed = run_converter(
        "build",
        "--source-pdf",
        str(tmp_path / "missing.pdf"),
        "--ocr-output",
        str(sample),
        "--output",
        str(tmp_path / "out.bookmd"),
    )

    assert completed.returncode == 1
    assert "Source PDF does not exist" in completed.stdout


def test_cli_reports_missing_result_md(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.json").write_text('{"blocks":[]}', encoding="utf-8")
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    completed = run_converter(
        "build",
        "--source-pdf",
        str(pdf),
        "--ocr-output",
        str(sample),
        "--output",
        str(tmp_path / "out.bookmd"),
    )

    assert completed.returncode == 1
    assert "result.md does not exist" in completed.stdout


def test_cli_reports_empty_ocr_blocks(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# Intro", encoding="utf-8")
    (sample / "result.json").write_text('{"blocks":[]}', encoding="utf-8")
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    completed = run_converter(
        "build",
        "--source-pdf",
        str(pdf),
        "--ocr-output",
        str(sample),
        "--output",
        str(tmp_path / "out.bookmd"),
    )

    assert completed.returncode == 1
    assert "OCR result contains no blocks" in completed.stdout


def test_cli_reports_invalid_result_json_without_traceback(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# Intro", encoding="utf-8")
    (sample / "result.json").write_text("{not json", encoding="utf-8")
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    completed = run_converter(
        "build",
        "--source-pdf",
        str(pdf),
        "--ocr-output",
        str(sample),
        "--output",
        str(tmp_path / "out.bookmd"),
    )

    assert completed.returncode == 1
    assert "result.json is not valid JSON" in completed.stdout
    assert "Traceback" not in completed.stderr


def test_cli_reports_missing_deepseek_api_key_without_traceback(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    sample = make_minimal_ocr_dir(tmp_path)
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    completed = run_converter(
        "build",
        "--source-pdf",
        str(pdf),
        "--ocr-output",
        str(sample),
        "--output",
        str(tmp_path / "out.bookmd"),
        "--translate",
        "true",
        "--provider",
        "deepseek",
    )

    assert completed.returncode == 1
    assert "DEEPSEEK_API_KEY is required" in completed.stdout
    assert "Traceback" not in completed.stderr
