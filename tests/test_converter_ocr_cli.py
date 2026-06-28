import json
import zipfile

from converter import cli, ocr_pipeline


class FakeOcrClient:
    def __init__(self):
        self.calls = []

    def parse_pdf(self, source_pdf):
        self.calls.append(source_pdf.name)
        return {
            "metadata": {"title": "OCR CLI Book"},
            "blocks": [
                {
                    "block_id": "h1",
                    "page": 1,
                    "type": "heading",
                    "level": 1,
                    "text": "Chapter 1",
                    "bbox": [0, 0, 10, 10],
                },
                {
                    "block_id": "p1",
                    "page": 1,
                    "type": "paragraph",
                    "text": "Grid inverter",
                    "bbox": [0, 20, 100, 40],
                },
            ],
        }


def test_cli_ocr_writes_standard_output(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "ocr_output"
    fake_client = FakeOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: fake_client)

    exit_code = cli.main(
        [
            "ocr",
            "--source-pdf",
            str(pdf),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert fake_client.calls == ["source.pdf"]
    assert (output_dir / "result.json").exists()
    assert (output_dir / "result.md").exists()


def test_cli_build_from_pdf_runs_ocr_then_builds_bookmd(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    ocr_output = tmp_path / "ocr_output"
    bookmd = tmp_path / "book.bookmd"
    fake_client = FakeOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: fake_client)

    exit_code = cli.main(
        [
            "build-from-pdf",
            "--source-pdf",
            str(pdf),
            "--ocr-output",
            str(ocr_output),
            "--output",
            str(bookmd),
            "--translate",
            "false",
        ]
    )

    assert exit_code == 0
    with zipfile.ZipFile(bookmd) as zf:
        manifest = json.loads(zf.read("book.json"))
        chapter = zf.read("chapters/001_chapter_1.md").decode("utf-8")

    assert manifest["title"] == "OCR CLI Book"
    assert "Grid inverter" in chapter


def test_cli_ocr_health_prints_service_status(monkeypatch, capsys):
    class FakeHealthClient:
        def check_health(self):
            return {"status": "ok", "service": "pdf_ocr_deploy"}

    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: FakeHealthClient())

    exit_code = cli.main(["ocr-health"])

    assert exit_code == 0
    assert "pdf_ocr_deploy" in capsys.readouterr().out
