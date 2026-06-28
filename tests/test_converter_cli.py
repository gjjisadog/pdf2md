import json
import subprocess
import sys

from bookmd_core import validate_bookmd


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
