import json

import pytest

from ocr_client import (
    MissingOcrConfigError,
    OcrApiConfig,
    OcrHttpClient,
    OcrJobClient,
    write_ocr_output,
)


def test_ocr_config_requires_api_url(monkeypatch):
    monkeypatch.delenv("OCR_API_URL", raising=False)

    with pytest.raises(MissingOcrConfigError):
        OcrApiConfig.from_env()


def test_ocr_http_client_uses_fake_transport_and_validates_blocks(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    requests = []

    def fake_transport(pdf_bytes, filename, config):
        requests.append((pdf_bytes, filename, config.api_url))
        return {
            "metadata": {"title": "OCR Book"},
            "blocks": [
                {
                    "block_id": "p001_b001",
                    "page": 1,
                    "type": "paragraph",
                    "text": "Grid inverter",
                    "bbox": [1, 2, 3, 4],
                }
            ],
        }

    client = OcrHttpClient(
        OcrApiConfig(api_url="https://ocr.example.test", api_key="test-key"),
        transport=fake_transport,
    )

    result = client.parse_pdf(pdf)

    assert requests == [(b"%PDF-1.4 test", "source.pdf", "https://ocr.example.test")]
    assert result["metadata"]["title"] == "OCR Book"
    assert result["blocks"][0]["block_id"] == "p001_b001"


def test_write_ocr_output_creates_standard_files(tmp_path):
    output_dir = tmp_path / "ocr_output"
    response = {
        "metadata": {"title": "OCR Book"},
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

    write_ocr_output(response, output_dir)

    result_json = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    result_md = (output_dir / "result.md").read_text(encoding="utf-8")
    parse_log = (output_dir / "parse.log").read_text(encoding="utf-8")

    assert result_json["metadata"]["title"] == "OCR Book"
    assert result_json["blocks"][1]["text"] == "Grid inverter"
    assert "# Chapter 1" in result_md
    assert "Grid inverter" in result_md
    assert "blocks=2" in parse_log


def test_ocr_job_client_checks_health_and_downloads_job_files(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 job")
    output_dir = tmp_path / "ocr_output"
    calls = []

    def fake_health(config):
        calls.append(("health", config.api_url))
        return {"status": "ok", "service": "pdf_ocr_deploy"}

    def fake_submit(pdf_bytes, filename, config):
        calls.append(("submit", pdf_bytes, filename, config.device))
        return {
            "job_id": "job-123",
            "status": "succeeded",
            "device": "gpu",
            "files": {
                "result_md": "/v1/jobs/job-123/files/result.md",
                "result_json": "/v1/jobs/job-123/files/result.json",
                "source_map": "/v1/jobs/job-123/files/source_map.json",
                "parse_log": "/v1/jobs/job-123/files/parse.log",
            },
        }

    def fake_download(file_url, config):
        calls.append(("download", file_url, config.api_key))
        if file_url.endswith("result.md"):
            return b"# Chapter 1\n\nGrid inverter\n"
        if file_url.endswith("result.json"):
            return json.dumps(
                {
                    "metadata": {"title": "Job Book"},
                    "blocks": [
                        {
                            "block_id": "p1",
                            "page": 1,
                            "type": "paragraph",
                            "text": "Grid inverter",
                            "bbox": [1, 2, 3, 4],
                        }
                    ],
                }
            ).encode("utf-8")
        if file_url.endswith("source_map.json"):
            return b'{"blocks":[]}\n'
        return b"job ok\n"

    client = OcrJobClient(
        OcrApiConfig(
            api_url="http://100.64.0.10:8765",
            api_key="secret",
            device="gpu",
        ),
        health_transport=fake_health,
        submit_transport=fake_submit,
        download_transport=fake_download,
    )

    health = client.check_health()
    client.parse_to_output(pdf, output_dir)

    assert health["service"] == "pdf_ocr_deploy"
    assert ("submit", b"%PDF-1.4 job", "source.pdf", "gpu") in calls
    assert (output_dir / "result.md").read_text(encoding="utf-8").startswith("# Chapter 1")
    assert json.loads((output_dir / "result.json").read_text(encoding="utf-8"))["metadata"]["title"] == "Job Book"
    assert (output_dir / "source_map.json").exists()
    assert (output_dir / "parse.log").read_text(encoding="utf-8") == "job ok\n"
