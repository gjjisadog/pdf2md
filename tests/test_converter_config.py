import json
import subprocess
import sys
import zipfile


def test_cli_build_reads_config_yaml_defaults(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# Intro", encoding="utf-8")
    (sample / "result.json").write_text(
        json.dumps(
            {
                "metadata": {"title": "Configured Book", "author": "Ada"},
                "blocks": [
                    {
                        "block_id": "h1",
                        "page": 1,
                        "type": "heading",
                        "level": 1,
                        "text": "Intro",
                        "bbox": [0, 0, 10, 10],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    config = tmp_path / "config.yaml"
    config.write_text(
        "\n".join(
            [
                "translation:",
                "  default_target_lang: en",
                "output:",
                "  save_original_pdf: false",
                "reading:",
                "  layout: scroll",
                "  theme: dark",
                "  font_size: 20",
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "configured.bookmd"

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
            "--config",
            str(config),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("book.json"))
        reading = json.loads(zf.read("reading_config.json"))

    assert "source/original.pdf" not in names
    assert manifest["title"] == "Configured Book"
    assert manifest["author"] == "Ada"
    assert manifest["language"] == "en"
    assert reading["layout"] == "scroll"
    assert reading["theme"] == "dark"
    assert reading["font_size"] == 20


def test_cli_target_lang_overrides_config_default(tmp_path):
    sample = tmp_path / "ocr"
    sample.mkdir()
    (sample / "result.md").write_text("# Intro", encoding="utf-8")
    (sample / "result.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "h1",
                        "page": 1,
                        "type": "heading",
                        "level": 1,
                        "text": "Intro",
                        "bbox": [0, 0, 10, 10],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    config = tmp_path / "config.yaml"
    config.write_text(
        "translation:\n  default_target_lang: en\n",
        encoding="utf-8",
    )
    output = tmp_path / "configured.bookmd"

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
            "--config",
            str(config),
            "--target-lang",
            "ja",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    with zipfile.ZipFile(output) as zf:
        manifest = json.loads(zf.read("book.json"))
        translation = json.loads(zf.read("translation.json"))

    assert manifest["language"] == "ja"
    assert translation["target_lang"] == "ja"
