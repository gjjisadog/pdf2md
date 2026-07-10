import json
import subprocess
import zipfile
from urllib.error import URLError

from converter import cli, ocr_pipeline
from ocr_client import OcrApiError


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


class FailingSecondBatchOcrClient(FakeBatchOcrClient):
    def parse_to_output(self, source_pdf, output_dir):
        if "batch_002" in source_pdf.name:
            self.calls.append(source_pdf.name)
            raise RuntimeError("simulated OCR outage for batch_002.pdf")
        super().parse_to_output(source_pdf, output_dir)


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

    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda timeout=None: FakeHealthClient())

    exit_code = cli.main(["ocr-health"])

    assert exit_code == 0
    assert "pdf_ocr_deploy" in capsys.readouterr().out


def test_cli_ocr_health_accepts_timeout_override(monkeypatch):
    captured = {}

    def fake_check_ocr_health(timeout=None):
        captured["timeout"] = timeout
        return {"status": "ok", "service": "pdf_ocr_deploy"}

    monkeypatch.setattr(cli, "check_ocr_health", fake_check_ocr_health)

    exit_code = cli.main(["ocr-health", "--timeout", "5"])

    assert exit_code == 0
    assert captured["timeout"] == 5


def test_check_ocr_health_uses_timeout_override(monkeypatch):
    captured = {}

    class FakeHealthClient:
        def __init__(self, config):
            captured["timeout"] = config.timeout

        def check_health(self):
            return {"status": "ok", "service": "pdf_ocr_deploy"}

    monkeypatch.setenv("OCR_API_URL", "http://100.100.134.95:8765")
    monkeypatch.setattr(ocr_pipeline, "OcrJobClient", FakeHealthClient)

    health = ocr_pipeline.check_ocr_health(timeout=7)

    assert health["status"] == "ok"
    assert captured["timeout"] == 7


def test_cli_ocr_health_reports_network_failure_without_traceback(monkeypatch, capsys):
    class FailingHealthClient:
        def check_health(self):
            raise URLError("connection refused")

    monkeypatch.setenv("OCR_API_URL", "http://100.100.134.95:8765")
    monkeypatch.setenv("OCR_API_KEY", "secret")
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda timeout=None: FailingHealthClient())

    exit_code = cli.main(["ocr-health"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "OCR API unreachable" in captured.out
    assert "http://100.100.134.95:8765" in captured.out
    assert "OCR_API_KEY is configured" in captured.out
    assert "secret" not in captured.out
    assert "Traceback" not in captured.err


def test_cli_ocr_reports_api_error_without_traceback(tmp_path, monkeypatch, capsys):
    class FailingOcrClient:
        def parse_to_output(self, _source_pdf, _output_dir):
            raise OcrApiError("OCR job result.json is not valid JSON")

    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda timeout=None: FailingOcrClient())

    exit_code = cli.main(
        [
            "ocr",
            "--source-pdf",
            str(pdf),
            "--output-dir",
            str(tmp_path / "ocr_output"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: OCR job result.json is not valid JSON" in captured.out
    assert "Traceback" not in captured.err


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
        lambda _source, _batch_size, _work_dir, _max_pages=None, _page_range=None: [
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
    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert [block["block_id"] for block in source_map["blocks"]] == ["p001_b001", "p002_b001"]
    assert [block["source_page"] for block in source_map["blocks"]] == [1, 2]
    assert source_map["blocks"][0]["source_text"] == "Page 1 text"


def test_ocr_batch_merge_rerenders_markdown_from_normalized_blocks(tmp_path):
    batch_pdf = tmp_path / "batch_001.pdf"
    batch_pdf.write_bytes(b"%PDF-1.4")
    batch_output = tmp_path / "batch_001"
    batch_output.mkdir()
    batch_result = {
        "pages": [
            {
                "page_index": 1,
                "blocks": [
                    {
                        "type": "table",
                        "text": "<html><body><table><tr><td>Type</td><td>Value</td></tr><tr><td>A</td><td>1</td></tr></table></body></html>",
                        "markdown": "<html><body><table><tr><td>Type</td><td>Value</td></tr><tr><td>A</td><td>1</td></tr></table></body></html>",
                        "bbox": [1, 2, 3, 4],
                    },
                    {
                        "type": "formula",
                        "text": "\\begin{aligned}x=y\\end{aligned}",
                        "bbox": [5, 6, 7, 8],
                    },
                ],
            }
        ]
    }
    (batch_output / "result.json").write_text(json.dumps(batch_result), encoding="utf-8")
    (batch_output / "result.md").write_text("<html><body><table>raw</table></body></html>\n", encoding="utf-8")
    (batch_output / "parse.log").write_text("ok\n", encoding="utf-8")
    output_dir = tmp_path / "ocr_output"

    ocr_pipeline.merge_ocr_batch_outputs(
        [(ocr_pipeline.OcrBatch(path=batch_pdf, first_page=4), batch_output)],
        output_dir,
    )

    result_md = (output_dir / "result.md").read_text(encoding="utf-8")

    assert "| Type | Value |" in result_md
    assert "$$" in result_md
    assert "\\begin{aligned}x=y\\end{aligned}" in result_md
    assert "<table>" not in result_md
    assert "p004_b001" in result_md


def test_cli_ocr_batch_resumes_completed_persisted_batches(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "ocr_output"
    batch_one = tmp_path / "batch_001.pdf"
    batch_two = tmp_path / "batch_002.pdf"
    batch_one.write_bytes(b"batch one")
    batch_two.write_bytes(b"batch two")
    persisted_batch_one = output_dir / "batches" / "batch_001"
    persisted_batch_one.mkdir(parents=True)
    (persisted_batch_one / "result.md").write_text("Persisted page 1\n", encoding="utf-8")
    (persisted_batch_one / "result.json").write_text(
        json.dumps(
            {
                "pages": [
                    {
                        "page_index": 1,
                        "blocks": [
                            {
                                "block_id": "old",
                                "type": "paragraph",
                                "text": "Persisted page 1",
                                "bbox": [1, 2, 3, 4],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (persisted_batch_one / "parse.log").write_text("persisted batch 1 ok\n", encoding="utf-8")
    fake_client = FakeBatchOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: fake_client)
    monkeypatch.setattr(
        ocr_pipeline,
        "split_pdf_batches",
        lambda _source, _batch_size, _work_dir, _max_pages=None, _page_range=None: [
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
    manifest = json.loads((output_dir / "batch_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert fake_client.calls == ["batch_002.pdf"]
    assert [page["page_index"] for page in result_json["pages"]] == [1, 2]
    assert "Persisted page 1" in result_md
    assert "Page 2 text" in result_md
    assert [batch["status"] for batch in manifest["batches"]] == ["succeeded", "succeeded"]


def test_ocr_batch_failure_keeps_successful_batches_and_can_resume(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "ocr_output"
    batch_one = tmp_path / "batch_001.pdf"
    batch_two = tmp_path / "batch_002.pdf"
    batch_one.write_bytes(b"batch one")
    batch_two.write_bytes(b"batch two")
    monkeypatch.setattr(
        ocr_pipeline,
        "split_pdf_batches",
        lambda _source, _batch_size, _work_dir, _max_pages=None, _page_range=None: [
            ocr_pipeline.OcrBatch(path=batch_one, first_page=1),
            ocr_pipeline.OcrBatch(path=batch_two, first_page=2),
        ],
    )

    failing_client = FailingSecondBatchOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: failing_client)

    try:
        ocr_pipeline.run_ocr(
            ocr_pipeline.OcrOptions(
                source_pdf=pdf,
                output_dir=output_dir,
                batch_size=1,
                max_pages=2,
            )
        )
    except RuntimeError as exc:
        assert "simulated OCR outage" in str(exc)
    else:
        raise AssertionError("Expected second OCR batch to fail")

    failed_manifest = json.loads((output_dir / "batch_manifest.json").read_text(encoding="utf-8"))
    assert failing_client.calls == ["batch_001.pdf", "batch_002.pdf"]
    assert [batch["status"] for batch in failed_manifest["batches"]] == ["succeeded", "failed"]
    assert "simulated OCR outage" in failed_manifest["batches"][1]["error"]
    assert (output_dir / "batches" / "batch_001" / "result.json").exists()
    assert not (output_dir / "result.json").exists()

    resumed_client = FakeBatchOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: resumed_client)

    ocr_pipeline.run_ocr(
        ocr_pipeline.OcrOptions(
            source_pdf=pdf,
            output_dir=output_dir,
            batch_size=1,
            max_pages=2,
        )
    )

    result_json = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    resumed_manifest = json.loads((output_dir / "batch_manifest.json").read_text(encoding="utf-8"))

    assert resumed_client.calls == ["batch_002.pdf"]
    assert [batch["status"] for batch in resumed_manifest["batches"]] == ["succeeded", "succeeded"]
    assert [page["page_index"] for page in result_json["pages"]] == [1, 2]
    assert "Page 1 text" in (output_dir / "result.md").read_text(encoding="utf-8")
    assert "Page 2 text" in (output_dir / "result.md").read_text(encoding="utf-8")


def test_pdfkit_splitter_limits_last_batch_to_max_pages(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4")
    calls = []

    monkeypatch.setattr(ocr_pipeline, "_pdfkit_page_count", lambda _source, _script: 10)

    def fake_run(command, text, capture_output, check):
        calls.append(command)
        output = tmp_path / command[4]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"%PDF-1.4 batch")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(ocr_pipeline.subprocess, "run", fake_run)

    batches = ocr_pipeline._split_pdf_batches_with_pdfkit(
        source,
        batch_size=2,
        work_dir=tmp_path / "work",
        max_pages=5,
    )

    assert [batch.first_page for batch in batches] == [1, 3, 5]
    assert [command[6] for command in calls] == ["2", "2", "1"]


def test_cli_ocr_batch_accepts_page_range(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "ocr_output"
    batch_one = tmp_path / "batch_001.pdf"
    batch_one.write_bytes(b"batch")
    captured = {}
    fake_client = FakeBatchOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: fake_client)

    def fake_split(source, batch_size, work_dir, max_pages=None, page_range=None):
        captured["source"] = source
        captured["batch_size"] = batch_size
        captured["max_pages"] = max_pages
        captured["page_range"] = page_range
        return [ocr_pipeline.OcrBatch(path=batch_one, first_page=21)]

    monkeypatch.setattr(ocr_pipeline, "split_pdf_batches", fake_split)

    exit_code = cli.main(
        [
            "ocr",
            "--source-pdf",
            str(pdf),
            "--output-dir",
            str(output_dir),
            "--batch-size",
            "3",
            "--page-range",
            "21-28",
        ]
    )

    result_json = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "batch_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert captured["page_range"] == (21, 28)
    assert captured["max_pages"] is None
    assert result_json["pages"][0]["page_index"] == 21
    assert result_json["pages"][0]["blocks"][0]["block_id"] == "p021_b001"
    assert manifest["page_range"] == [21, 28]


def test_cli_ocr_page_range_without_batch_size_splits_selected_range(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "ocr_output"
    batch_one = tmp_path / "batch_001.pdf"
    batch_one.write_bytes(b"batch")
    captured = {}
    fake_client = FakeBatchOcrClient()
    monkeypatch.setattr(ocr_pipeline, "_ocr_client_from_env", lambda: fake_client)

    def fake_split(source, batch_size, work_dir, max_pages=None, page_range=None):
        captured["batch_size"] = batch_size
        captured["page_range"] = page_range
        return [ocr_pipeline.OcrBatch(path=batch_one, first_page=5)]

    monkeypatch.setattr(ocr_pipeline, "split_pdf_batches", fake_split)

    exit_code = cli.main(
        [
            "ocr",
            "--source-pdf",
            str(pdf),
            "--output-dir",
            str(output_dir),
            "--page-range",
            "5-7",
        ]
    )

    assert exit_code == 0
    assert fake_client.calls == ["batch_001.pdf"]
    assert captured["batch_size"] == 3
    assert captured["page_range"] == (5, 7)
