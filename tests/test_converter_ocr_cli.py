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


class FakeBatchOcrClient:
    def __init__(self):
        self.calls = []

    def parse_to_output(self, source_pdf, output_dir):
        self.calls.append(source_pdf.name)
        output_dir.mkdir(parents=True, exist_ok=True)
        page = 1 if "batch_001" in source_pdf.name else 2
        (output_dir / "result.md").write_text(f"Page {page} text\n", encoding="utf-8")
        (output_dir / "result.json").write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "page_index": 1,
                            "blocks": [
                                {
                                    "block_id": "p001_b001",
                                    "type": "paragraph",
                                    "text": f"Page {page} text",
                                    "bbox": [1, 2, 3, 4],
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (output_dir / "parse.log").write_text(f"batch {page} ok\n", encoding="utf-8")


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


def test_cli_ocr_batch_splits_and_merges_outputs(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "ocr_output"
    batch_one = tmp_path / "batch_001.pdf"
    batch_two = tmp_path / "batch_002.pdf"
    batch_one.write_bytes(b"batch one")
    batch_two.write_bytes(b"batch two")
    fake_client = FakeBatchOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: fake_client)
    monkeypatch.setattr(
        ocr_pipeline,
        "split_pdf_batches",
        lambda _source, _batch_size, _work_dir, _max_pages=None: [
            ocr_pipeline.OcrBatch(path=batch_one, first_page=1),
            ocr_pipeline.OcrBatch(path=batch_two, first_page=2),
        ],
    )

    exit_code = cli.main(
        [
            "ocr",
            "--source-pdf",
            str(pdf),
            "--output-dir",
            str(output_dir),
            "--batch-size",
            "1",
            "--max-pages",
            "2",
        ]
    )

    result_json = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    result_md = (output_dir / "result.md").read_text(encoding="utf-8")
    parse_log = (output_dir / "parse.log").read_text(encoding="utf-8")

    assert exit_code == 0
    assert fake_client.calls == ["batch_001.pdf", "batch_002.pdf"]
    assert [page["page_index"] for page in result_json["pages"]] == [1, 2]
    assert result_json["pages"][1]["blocks"][0]["block_id"] == "p002_b001"
    assert "Page 1 text" in result_md
    assert "Page 2 text" in result_md
    assert "batch 1 ok" in parse_log
    assert "batch 2 ok" in parse_log
