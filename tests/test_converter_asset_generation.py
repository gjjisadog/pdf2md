import json
import zipfile
from pathlib import Path

from converter import builder
from converter.builder import BuildOptions, build_bookmd
from converter.quality import inspect_bookmd
from source_map_core import OcrBlock


def test_generate_missing_block_assets_crops_media_blocks(tmp_path):
    page_image = tmp_path / "page_001.png"
    page_image.write_bytes(b"fake image")
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    assets_root = tmp_path / "assets"
    render_calls = []
    crop_calls = []

    def fake_renderer(_source_pdf: Path, page: int, _work_dir: Path) -> Path:
        render_calls.append(page)
        return page_image

    def fake_cropper(input_image: Path, bbox: list[float], output_path: Path) -> bool:
        crop_calls.append((input_image, bbox, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"cropped")
        return True

    blocks = [
        OcrBlock(
            block_id="fig:001",
            page=1,
            type="figure",
            bbox=[20, 30, 120, 150],
            text="Circuit diagram",
        ),
        OcrBlock(
            block_id="p001",
            page=1,
            type="paragraph",
            bbox=[0, 0, 50, 20],
            text="Body",
        ),
        OcrBlock(
            block_id="tbl001",
            page=1,
            type="table",
            bbox=[40, 50, 160, 180],
            text="Table caption",
            asset_path="assets/existing/table.png",
        ),
    ]

    updated = builder._generate_missing_block_assets(
        source_pdf,
        blocks,
        assets_root,
        page_renderer=fake_renderer,
        image_cropper=fake_cropper,
    )

    figure = updated[0]
    paragraph = updated[1]
    existing = updated[2]

    assert render_calls == [1]
    assert len(crop_calls) == 1
    assert figure.asset_path == "assets/generated/page_001_fig_001.png"
    assert paragraph.asset_path is None
    assert existing.asset_path == "assets/existing/table.png"
    assert (assets_root / "generated/page_001_fig_001.png").read_bytes() == b"cropped"


def test_generate_missing_block_assets_skips_when_renderer_unavailable(tmp_path):
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4")
    block = OcrBlock(
        block_id="fig001",
        page=1,
        type="figure",
        bbox=[20, 30, 120, 150],
        text="Circuit diagram",
    )

    def missing_renderer(_source_pdf: Path, _page: int, _work_dir: Path) -> Path | None:
        return None

    updated = builder._generate_missing_block_assets(
        source_pdf,
        [block],
        tmp_path / "assets",
        page_renderer=missing_renderer,
    )

    assert updated == [block]


def test_generate_missing_block_assets_records_optional_failures(tmp_path):
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    block = OcrBlock(
        block_id="fig-failed",
        page=3,
        type="figure",
        bbox=[20, 30, 120, 150],
        text="Unavailable diagram",
    )
    failures = []

    updated = builder._generate_missing_block_assets(
        source_pdf,
        [block],
        tmp_path / "assets",
        page_renderer=lambda _source, _page, _work_dir: None,
        failure_report=failures,
    )

    assert updated == [block]
    assert failures == [
        {
            "block_id": "fig-failed",
            "page": 3,
            "type": "figure",
            "reason": "page renderer unavailable",
        }
    ]


def test_generate_missing_block_assets_crops_formula_and_table_blocks(tmp_path):
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    page_image = tmp_path / "page.png"
    page_image.write_bytes(b"fake image")
    render_calls = []
    crop_calls = []

    def fake_renderer(_source_pdf: Path, page: int, _work_dir: Path) -> Path:
        render_calls.append(page)
        return page_image

    def fake_cropper(input_image: Path, bbox: list[float], output_path: Path) -> bool:
        crop_calls.append((input_image, bbox, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"cropped")
        return True

    blocks = [
        OcrBlock("formula001", 1, "formula", [10, 20, 110, 120], text="x=y"),
        OcrBlock("table001", 1, "table", [10, 20, 110, 120], text="table"),
    ]

    updated = builder._generate_missing_block_assets(
        source_pdf,
        blocks,
        tmp_path / "assets",
        page_renderer=fake_renderer,
        image_cropper=fake_cropper,
    )

    assert render_calls == [1]
    assert len(crop_calls) == 2
    assert [block.asset_path for block in updated] == [
        "assets/generated/page_001_formula001.png",
        "assets/generated/page_001_table001.png",
    ]


def test_generate_missing_block_assets_reuses_page_rendering_by_default(tmp_path, monkeypatch):
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    page_image = tmp_path / "page.png"
    page_image.write_bytes(b"fake image")
    render_calls = []
    crop_calls = []

    def fake_page_renderer(_source_pdf: Path, page: int, _work_dir: Path) -> Path:
        render_calls.append(page)
        return page_image

    def fake_cropper(input_image: Path, bbox: list[float], output_path: Path) -> bool:
        crop_calls.append((input_image, bbox, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"cropped")
        return True

    def fail_block_renderer(*_args, **_kwargs):
        raise AssertionError("per-block PDF rendering should not be used by default")

    monkeypatch.setattr(builder, "_render_pdf_page_image", fake_page_renderer)
    monkeypatch.setattr(builder, "_crop_page_image", fake_cropper)
    monkeypatch.setattr(builder, "_render_pdf_block_asset", fail_block_renderer)

    blocks = [
        OcrBlock("fig001", 1, "figure", [10, 20, 110, 120], text="figure"),
        OcrBlock("formula001", 1, "formula", [20, 40, 120, 140], text="x=y"),
        OcrBlock("fig002", 2, "figure", [10, 20, 110, 120], text="figure 2"),
    ]

    updated = builder._generate_missing_block_assets(source_pdf, blocks, tmp_path / "assets")

    assert render_calls == [1, 2]
    assert len(crop_calls) == 3
    assert [block.asset_path for block in updated] == [
        "assets/generated/page_001_fig001.png",
        "assets/generated/page_001_formula001.png",
        "assets/generated/page_002_fig002.png",
    ]


def test_crop_box_adds_margin_and_clamps_to_image_size():
    assert builder._crop_box([2, 3, 98, 99], (100, 100)) == (0, 0, 100, 100)
    assert builder._crop_box([20, 30, 120, 150], (200, 200)) == (12, 22, 128, 158)


def test_default_block_asset_renderer_uses_pdfkit_when_swift_is_available(tmp_path, monkeypatch):
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    output = tmp_path / "assets/generated/page_001_fig001.png"
    calls = []

    monkeypatch.setattr(builder.shutil, "which", lambda name: "/usr/bin/swift" if name == "swift" else None)

    def fake_run(command, text, capture_output, check, timeout):
        calls.append(command)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"png")
        return builder.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(builder.subprocess, "run", fake_run)

    rendered = builder._render_pdf_block_asset(
        source_pdf,
        page=1,
        bbox=[10, 20, 110, 120],
        output_path=output,
        work_dir=tmp_path / "work",
    )

    assert rendered == output
    assert output.read_bytes() == b"png"
    assert calls
    assert calls[0][1].endswith("crop_pdfkit.swift")


def test_pdf_page_renderer_creates_work_dir_before_running_pdftoppm(tmp_path, monkeypatch):
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    work_dir = tmp_path / "missing-work-dir"

    monkeypatch.setattr(builder.shutil, "which", lambda name: "/usr/bin/pdftoppm" if name == "pdftoppm" else None)

    def fake_run(command, text, capture_output, check, timeout):
        output = Path(command[-1]).with_suffix(".png")
        assert output.parent.exists()
        output.write_bytes(b"page")
        return builder.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(builder.subprocess, "run", fake_run)

    rendered = builder._render_pdf_page_image(source_pdf, 1, work_dir)

    assert rendered == work_dir / "page_001.png"
    assert rendered.read_bytes() == b"page"


def test_build_bookmd_preserves_cover_as_first_chapter_visual(tmp_path, monkeypatch):
    ocr = tmp_path / "ocr"
    ocr.mkdir()
    (ocr / "result.md").write_text("# Cover Title\n\nBody", encoding="utf-8")
    (ocr / "result.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "block_id": "h1",
                        "page": 1,
                        "type": "heading",
                        "level": 1,
                        "bbox": [0, 0, 100, 40],
                        "text": "Cover Title",
                    },
                    {
                        "block_id": "p1",
                        "page": 2,
                        "type": "paragraph",
                        "bbox": [0, 50, 100, 90],
                        "text": "Body",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    rendered_cover = tmp_path / "rendered-cover.png"
    rendered_cover.write_bytes(b"cover image")

    def fake_page_renderer(_source_pdf: Path, page: int, _work_dir: Path) -> Path:
        assert page == 1
        return rendered_cover

    monkeypatch.setattr(builder, "_render_pdf_page_image", fake_page_renderer)

    output = build_bookmd(
        BuildOptions(
            source_pdf=source_pdf,
            ocr_output=ocr,
            output=tmp_path / "cover.bookmd",
            translate=False,
        )
    )

    with zipfile.ZipFile(output) as zf:
        assert "assets/cover/page_001.png" in zf.namelist()
        assert zf.read("assets/cover/page_001.png") == b"cover image"
        first_chapter = zf.read("chapters/001_chapter_1.md").decode("utf-8")

    assert first_chapter.startswith("![Cover](../assets/cover/page_001.png)\n\n")
    assert inspect_bookmd(output).has_cover is True
