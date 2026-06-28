import json
import subprocess
import sys
import zipfile


def test_sample_ocr_output_builds_bookmd(tmp_path):
    output = tmp_path / "sample.bookmd"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "converter",
            "build",
            "--source-pdf",
            "samples/ocr_output_sample/original.pdf",
            "--ocr-output",
            "samples/ocr_output_sample",
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
    with zipfile.ZipFile(output) as zf:
        source_map = json.loads(zf.read("source_map.json"))
        search_index = json.loads(zf.read("search_index.json"))

    assert any(item["block_id"] == "p001_b002" for item in source_map["blocks"])
    assert any("并网逆变器" in item["text"] for item in search_index["items"])
