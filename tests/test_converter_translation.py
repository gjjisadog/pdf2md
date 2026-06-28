import json
import zipfile

from converter import builder
from converter.builder import BuildOptions, build_bookmd
from translator_core import TranslationResult


class CountingTranslator:
    def __init__(self):
        self.calls = []

    def translate_blocks(self, blocks, target_lang):
        self.calls.append([block.block_id for block in blocks])
        return [
            TranslationResult(
                block_id=block.block_id,
                source_text=block.text,
                translated_text=f"译文:{block.text}",
            )
            for block in blocks
        ]


def _write_sample_ocr(root):
    root.mkdir()
    (root / "result.md").write_text("# Intro\nVoltage source inverter", encoding="utf-8")
    (root / "result.json").write_text(
        json.dumps(
            {
                "metadata": {"title": "Translation Sample"},
                "blocks": [
                    {
                        "block_id": "h1",
                        "page": 1,
                        "type": "heading",
                        "level": 1,
                        "text": "Intro",
                        "bbox": [0, 0, 10, 10],
                    },
                    {
                        "block_id": "p1",
                        "page": 1,
                        "type": "paragraph",
                        "text": "The grid inverter uses a phase-locked loop (PLL).",
                        "bbox": [0, 20, 100, 40],
                    },
                    {
                        "block_id": "eq1",
                        "page": 1,
                        "type": "formula",
                        "latex": "G_i(s)=K_p+\\frac{K_i}{s}",
                        "text": "G_i(s)=K_p+K_i/s",
                        "bbox": [0, 50, 100, 70],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_converter_writes_translated_payloads_and_uses_cache(tmp_path, monkeypatch):
    ocr = tmp_path / "ocr"
    _write_sample_ocr(ocr)
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    cache_path = tmp_path / "cache.jsonl"
    output_one = tmp_path / "one.bookmd"
    output_two = tmp_path / "two.bookmd"
    translator = CountingTranslator()
    monkeypatch.setattr(builder, "_translator_for_options", lambda _options: translator)

    options = BuildOptions(
        source_pdf=pdf,
        ocr_output=ocr,
        output=output_one,
        translate=True,
        provider="noop",
        target_lang="zh",
        config={"translation": {"bilingual": True, "cache_path": str(cache_path)}},
    )
    build_bookmd(options)
    build_bookmd(
        BuildOptions(
            source_pdf=pdf,
            ocr_output=ocr,
            output=output_two,
            translate=True,
            provider="noop",
            target_lang="zh",
            config={"translation": {"bilingual": True, "cache_path": str(cache_path)}},
        )
    )

    assert translator.calls == [["h1", "p1", "eq1"]]
    with zipfile.ZipFile(output_one) as zf:
        chapter = zf.read("chapters/001_chapter_1.md").decode("utf-8")
        translation = json.loads(zf.read("translation.json"))
        terms = json.loads(zf.read("terms.json"))
        source_map = json.loads(zf.read("source_map.json"))
        search_index = json.loads(zf.read("search_index.json"))

    assert "译文:The grid inverter uses" in chapter
    assert "原文:" in chapter
    assert "$$\nG_i(s)=K_p+\\frac{K_i}{s}\n$$" in chapter
    assert translation["provider"] == "noop"
    assert translation["blocks"][0]["status"] == "translated"
    assert translation["blocks"][0]["cache_key"]
    assert translation["blocks"][0]["error"] == ""
    assert any(item["source"] == "grid inverter" for item in terms["terms"])
    assert any(item["translated_text"].startswith("译文:") for item in source_map["blocks"])
    assert any(item["text"].startswith("译文:") for item in search_index["items"])
