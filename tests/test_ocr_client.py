import base64
import json
from urllib.error import URLError

import pytest

import ocr_client.client as ocr_client_module

from ocr_client import (
    MissingOcrConfigError,
    OcrApiError,
    OcrApiConfig,
    OcrHttpClient,
    OcrJobClient,
    write_ocr_output,
)


def test_ocr_config_requires_api_url(monkeypatch):
    monkeypatch.delenv("OCR_API_URL", raising=False)

    with pytest.raises(MissingOcrConfigError):
        OcrApiConfig.from_env()


def test_ocr_config_reports_invalid_timeout(monkeypatch):
    monkeypatch.setenv("OCR_API_URL", "http://100.100.134.95:8765")
    monkeypatch.setenv("OCR_API_TIMEOUT", "abc")

    with pytest.raises(MissingOcrConfigError, match="OCR_API_TIMEOUT must be an integer"):
        OcrApiConfig.from_env()


def test_ocr_config_rejects_non_positive_timeout(monkeypatch):
    monkeypatch.setenv("OCR_API_URL", "http://100.100.134.95:8765")
    monkeypatch.setenv("OCR_API_TIMEOUT", "0")

    with pytest.raises(MissingOcrConfigError, match="OCR_API_TIMEOUT must be greater than 0"):
        OcrApiConfig.from_env()


def test_ocr_config_explicit_timeout_overrides_invalid_env_timeout(monkeypatch):
    monkeypatch.setenv("OCR_API_URL", "http://100.100.134.95:8765")
    monkeypatch.setenv("OCR_API_TIMEOUT", "abc")

    config = OcrApiConfig.from_env(timeout=3)

    assert config.timeout == 3


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
    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert [block["block_id"] for block in source_map["blocks"]] == ["h1", "p1"]
    assert source_map["blocks"][1]["source_page"] == 1


def test_write_ocr_output_writes_inline_assets_only_under_assets_directory(tmp_path):
    output_dir = tmp_path / "ocr_output"

    write_ocr_output(
        {
            "blocks": [],
            "assets": [
                {
                    "path": "assets/figures/page-001.png",
                    "content_base64": base64.b64encode(b"image data").decode("ascii"),
                }
            ],
        },
        output_dir,
    )

    assert (output_dir / "assets" / "figures" / "page-001.png").read_bytes() == b"image data"


@pytest.mark.parametrize(
    "unsafe_path",
    ["../outside.png", "/tmp/outside.png", "assets/../outside.png", r"assets\\outside.png"],
)
def test_write_ocr_output_rejects_unsafe_inline_asset_paths_before_writing(tmp_path, unsafe_path):
    output_dir = tmp_path / "ocr_output"

    with pytest.raises(OcrApiError, match="safe relative path"):
        write_ocr_output(
            {
                "blocks": [],
                "assets": [
                    {
                        "path": unsafe_path,
                        "content_base64": base64.b64encode(b"image data").decode("ascii"),
                    }
                ],
            },
            output_dir,
        )

    assert not output_dir.exists()


def test_write_ocr_output_rejects_invalid_base64_without_writing_prior_assets(tmp_path):
    output_dir = tmp_path / "ocr_output"

    with pytest.raises(OcrApiError, match="invalid base64 content"):
        write_ocr_output(
            {
                "blocks": [],
                "assets": [
                    {
                        "path": "assets/valid.png",
                        "content_base64": base64.b64encode(b"valid image").decode("ascii"),
                    },
                    {"path": "assets/invalid.png", "content_base64": "not base64!"},
                ],
            },
            output_dir,
        )

    assert not output_dir.exists()


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
    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert [block["block_id"] for block in source_map["blocks"]] == ["p1"]
    assert source_map["blocks"][0]["source_text"] == "Grid inverter"
    assert (output_dir / "parse.log").read_text(encoding="utf-8") == "job ok\n"


def test_ocr_job_client_rejects_cross_origin_file_urls_before_downloading(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 unsafe job")
    download_calls = []

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-cross-origin",
            "status": "succeeded",
            "files": {
                "result_md": "https://attacker.example.test/result.md",
                "result_json": "/v1/jobs/job-cross-origin/files/result.json",
                "parse_log": "/v1/jobs/job-cross-origin/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        download_calls.append(file_url)
        return b"unexpected"

    client = OcrJobClient(
        OcrApiConfig(api_url="https://ocr.example.test", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    with pytest.raises(OcrApiError, match="same origin"):
        client.parse_to_output(pdf, tmp_path / "ocr_output")

    assert download_calls == []


def test_ocr_job_client_allows_same_origin_absolute_file_urls(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 same origin")
    file_base = "https://ocr.example.test:8443/v1/jobs/job-same-origin/files"
    download_calls = []

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-same-origin",
            "status": "succeeded",
            "files": {
                "result_md": f"{file_base}/result.md",
                "result_json": f"{file_base}/result.json",
                "parse_log": f"{file_base}/parse.log",
            },
        }

    def fake_download(file_url, _config):
        download_calls.append(file_url)
        if file_url.endswith("result.md"):
            return b"Same-origin download\n"
        if file_url.endswith("result.json"):
            return b'{"blocks": []}'
        return b"same-origin log\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="https://ocr.example.test:8443/api", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    output_dir = tmp_path / "ocr_output"
    client.parse_to_output(pdf, output_dir)

    assert download_calls == [
        f"{file_base}/result.md",
        f"{file_base}/result.json",
        f"{file_base}/parse.log",
    ]
    assert (output_dir / "result.md").read_bytes() == b"Same-origin download\n"


def test_job_download_refuses_cross_origin_url_before_sending_authorization(monkeypatch):
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc_value, _traceback):
            return False

        def read(self):
            return b"same-origin content"

    def fake_job_urlopen(http_request, timeout):
        requests.append((http_request, timeout))
        return FakeResponse()

    monkeypatch.setattr(ocr_client_module, "_job_urlopen", fake_job_urlopen)
    config = OcrApiConfig(api_url="https://ocr.example.test", api_key="secret")

    assert (
        ocr_client_module._job_download_transport("/v1/jobs/job-1/files/result.md", config)
        == b"same-origin content"
    )
    assert requests[0][0].get_header("Authorization") == "Bearer secret"

    with pytest.raises(OcrApiError, match="same origin"):
        ocr_client_module._job_download_transport("https://attacker.example.test/result.md", config)

    assert len(requests) == 1


def test_ocr_job_client_polls_queued_jobs_before_downloading(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 queued")
    output_dir = tmp_path / "ocr_output"
    status_calls = []

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-queued",
            "status": "queued",
            "files": {
                "result_md": "/v1/jobs/job-queued/files/result.md",
                "result_json": "/v1/jobs/job-queued/files/result.json",
                "parse_log": "/v1/jobs/job-queued/files/parse.log",
            },
        }

    def fake_status(job_id, _config):
        status_calls.append(job_id)
        return {
            "job_id": job_id,
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-queued/files/result.md",
                "result_json": "/v1/jobs/job-queued/files/result.json",
                "parse_log": "/v1/jobs/job-queued/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.md"):
            return b"Queued job text\n"
        if file_url.endswith("result.json"):
            return b'{"pages":[{"page_index":2,"blocks":[]}]}'
        return b"queued ok\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        status_transport=fake_status,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    assert status_calls == ["job-queued"]
    assert (output_dir / "result.md").read_text(encoding="utf-8") == "Queued job text\n"


def test_ocr_job_client_generates_source_map_when_job_omits_file(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 no source map")
    output_dir = tmp_path / "ocr_output"

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-no-source-map",
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-no-source-map/files/result.md",
                "result_json": "/v1/jobs/job-no-source-map/files/result.json",
                "parse_log": "/v1/jobs/job-no-source-map/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.md"):
            return b"Fallback source map text\n"
        if file_url.endswith("result.json"):
            return json.dumps(
                {
                    "blocks": [
                        {
                            "block_id": "p1",
                            "page": 3,
                            "type": "paragraph",
                            "text": "Fallback source map text",
                            "bbox": [1, 2, 30, 40],
                        }
                    ]
                }
            ).encode("utf-8")
        return b"no source map ok\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert source_map["blocks"][0]["block_id"] == "p1"
    assert source_map["blocks"][0]["source_page"] == 3
    assert source_map["blocks"][0]["source_text"] == "Fallback source map text"


def test_ocr_job_client_regenerates_source_map_when_block_ids_do_not_align(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 misaligned source map")
    output_dir = tmp_path / "ocr_output"

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-misaligned-source-map",
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-misaligned-source-map/files/result.md",
                "result_json": "/v1/jobs/job-misaligned-source-map/files/result.json",
                "source_map": "/v1/jobs/job-misaligned-source-map/files/source_map.json",
                "parse_log": "/v1/jobs/job-misaligned-source-map/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.md"):
            return b"Aligned source map text\n"
        if file_url.endswith("result.json"):
            return json.dumps(
                {
                    "blocks": [
                        {
                            "block_id": "p1",
                            "page": 4,
                            "type": "paragraph",
                            "text": "Aligned source map text",
                            "bbox": [1, 2, 30, 40],
                        }
                    ]
                }
            ).encode("utf-8")
        if file_url.endswith("source_map.json"):
            return b'{"blocks":[{"block_id":"wrong","source_page":99,"source_text":"wrong"}]}\n'
        return b"misaligned source map log\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert [block["block_id"] for block in source_map["blocks"]] == ["p1"]
    assert source_map["blocks"][0]["source_page"] == 4
    assert source_map["blocks"][0]["source_text"] == "Aligned source map text"


def test_ocr_job_client_regenerates_source_map_when_source_pages_do_not_align(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 wrong source page")
    output_dir = tmp_path / "ocr_output"

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-wrong-source-page",
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-wrong-source-page/files/result.md",
                "result_json": "/v1/jobs/job-wrong-source-page/files/result.json",
                "source_map": "/v1/jobs/job-wrong-source-page/files/source_map.json",
                "parse_log": "/v1/jobs/job-wrong-source-page/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.md"):
            return b"Correct source page text\n"
        if file_url.endswith("result.json"):
            return json.dumps(
                {
                    "blocks": [
                        {
                            "block_id": "p1",
                            "page": 4,
                            "type": "paragraph",
                            "text": "Correct source page text",
                            "bbox": [1, 2, 30, 40],
                        }
                    ]
                }
            ).encode("utf-8")
        if file_url.endswith("source_map.json"):
            return b'{"blocks":[{"block_id":"p1","source_page":99,"source_text":"Correct source page text"}]}\n'
        return b"wrong source page log\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert source_map["blocks"][0]["block_id"] == "p1"
    assert source_map["blocks"][0]["source_page"] == 4
    assert source_map["blocks"][0]["source_text"] == "Correct source page text"


def test_ocr_job_client_regenerates_source_map_when_bbox_does_not_align(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 wrong bbox")
    output_dir = tmp_path / "ocr_output"

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-wrong-bbox",
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-wrong-bbox/files/result.md",
                "result_json": "/v1/jobs/job-wrong-bbox/files/result.json",
                "source_map": "/v1/jobs/job-wrong-bbox/files/source_map.json",
                "parse_log": "/v1/jobs/job-wrong-bbox/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.md"):
            return b"Correct bbox text\n"
        if file_url.endswith("result.json"):
            return json.dumps(
                {
                    "blocks": [
                        {
                            "block_id": "p1",
                            "page": 4,
                            "type": "paragraph",
                            "text": "Correct bbox text",
                            "bbox": [1, 2, 30, 40],
                        }
                    ]
                }
            ).encode("utf-8")
        if file_url.endswith("source_map.json"):
            return b'{"blocks":[{"block_id":"p1","source_page":4,"bbox":[9,9,9,9],"source_text":"Correct bbox text"}]}\n'
        return b"wrong bbox log\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert source_map["blocks"][0]["block_id"] == "p1"
    assert source_map["blocks"][0]["source_page"] == 4
    assert source_map["blocks"][0]["bbox"] == [1, 2, 30, 40]


def test_ocr_job_client_regenerates_source_map_when_source_text_does_not_align(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 wrong source text")
    output_dir = tmp_path / "ocr_output"

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-wrong-source-text",
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-wrong-source-text/files/result.md",
                "result_json": "/v1/jobs/job-wrong-source-text/files/result.json",
                "source_map": "/v1/jobs/job-wrong-source-text/files/source_map.json",
                "parse_log": "/v1/jobs/job-wrong-source-text/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.md"):
            return b"Correct source text\n"
        if file_url.endswith("result.json"):
            return json.dumps(
                {
                    "blocks": [
                        {
                            "block_id": "p1",
                            "page": 4,
                            "type": "paragraph",
                            "text": "Correct source text",
                            "bbox": [1, 2, 30, 40],
                        }
                    ]
                }
            ).encode("utf-8")
        if file_url.endswith("source_map.json"):
            return b'{"blocks":[{"block_id":"p1","source_page":4,"bbox":[1,2,30,40],"source_text":"Wrong source text"}]}\n'
        return b"wrong source text log\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    source_map = json.loads((output_dir / "source_map.json").read_text(encoding="utf-8"))
    assert source_map["blocks"][0]["block_id"] == "p1"
    assert source_map["blocks"][0]["source_page"] == 4
    assert source_map["blocks"][0]["bbox"] == [1, 2, 30, 40]
    assert source_map["blocks"][0]["source_text"] == "Correct source text"


def test_ocr_job_client_reports_invalid_result_json_readably(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 invalid json")
    output_dir = tmp_path / "ocr_output"

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-bad-json",
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-bad-json/files/result.md",
                "result_json": "/v1/jobs/job-bad-json/files/result.json",
                "parse_log": "/v1/jobs/job-bad-json/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.json"):
            return b"{not json"
        if file_url.endswith("result.md"):
            return b"Bad json text\n"
        return b"bad json log\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    with pytest.raises(OcrApiError, match="OCR job result.json is not valid JSON"):
        client.parse_to_output(pdf, output_dir)


def test_ocr_job_client_retries_transient_status_errors(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 queued")
    output_dir = tmp_path / "ocr_output"
    status_calls = []

    def fake_submit(_pdf_bytes, _filename, _config):
        return {"job_id": "job-retry", "status": "queued"}

    def fake_status(job_id, _config):
        status_calls.append(job_id)
        if len(status_calls) == 1:
            raise URLError("temporary network timeout")
        return {
            "job_id": job_id,
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-retry/files/result.md",
                "result_json": "/v1/jobs/job-retry/files/result.json",
                "parse_log": "/v1/jobs/job-retry/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        if file_url.endswith("result.md"):
            return b"Recovered text\n"
        if file_url.endswith("result.json"):
            return b'{"pages":[{"page_index":1,"blocks":[]}]}'
        return b"retry ok\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        status_transport=fake_status,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    assert status_calls == ["job-retry", "job-retry"]
    assert (output_dir / "result.md").read_text(encoding="utf-8") == "Recovered text\n"


def test_ocr_job_client_retries_transient_download_errors(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 done")
    output_dir = tmp_path / "ocr_output"
    download_calls = []

    def fake_submit(_pdf_bytes, _filename, _config):
        return {
            "job_id": "job-download",
            "status": "succeeded",
            "files": {
                "result_md": "/v1/jobs/job-download/files/result.md",
                "result_json": "/v1/jobs/job-download/files/result.json",
                "parse_log": "/v1/jobs/job-download/files/parse.log",
            },
        }

    def fake_download(file_url, _config):
        download_calls.append(file_url)
        if file_url.endswith("result.md") and download_calls.count(file_url) == 1:
            raise URLError("temporary download timeout")
        if file_url.endswith("result.md"):
            return b"Downloaded after retry\n"
        if file_url.endswith("result.json"):
            return b'{"pages":[{"page_index":1,"blocks":[]}]}'
        return b"download ok\n"

    client = OcrJobClient(
        OcrApiConfig(api_url="http://100.64.0.10:8765", api_key="secret"),
        submit_transport=fake_submit,
        download_transport=fake_download,
        poll_interval_seconds=0,
        retry_delay_seconds=0,
    )

    client.parse_to_output(pdf, output_dir)

    assert download_calls.count("/v1/jobs/job-download/files/result.md") == 2
    assert (output_dir / "result.md").read_text(encoding="utf-8") == "Downloaded after retry\n"
