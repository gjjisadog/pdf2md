from pathlib import Path

from PIL import Image, ImageDraw

from bookmd_core.visuals import crop_image, render_pdf_page
from converter import builder
from source_map_core import OcrBlock


def _make_pdf(path: Path) -> None:
    image = Image.new("RGB", (320, 220), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 50, 280, 180), fill=(25, 95, 180))
    draw.ellipse((120, 80, 200, 150), fill=(240, 180, 40))
    image.save(path, "PDF", resolution=72.0)


def test_pdfium_and_pillow_render_and_crop_without_host_tools(tmp_path, monkeypatch):
    source_pdf = tmp_path / "visual.pdf"
    _make_pdf(source_pdf)
    page_image = tmp_path / "page.png"
    cropped = tmp_path / "cropped.png"
    monkeypatch.setattr(builder.shutil, "which", lambda _name: None)

    rendered = render_pdf_page(source_pdf, 1, page_image, scale=2.0)
    assert rendered == page_image
    assert page_image.exists()
    assert crop_image(page_image, [40, 50, 280, 180], cropped)

    with Image.open(page_image) as image, Image.open(cropped) as crop:
        assert image.width > 300
        assert image.height > 200
        assert crop.width > 0
        assert crop.height > 0


def test_builder_default_page_renderer_uses_portable_backend(tmp_path, monkeypatch):
    source_pdf = tmp_path / "visual.pdf"
    _make_pdf(source_pdf)
    work_dir = tmp_path / "work"
    monkeypatch.setattr(builder.shutil, "which", lambda _name: None)

    rendered = builder._render_pdf_page_image(source_pdf, 1, work_dir)

    assert rendered == work_dir / "page_001.png"
    assert rendered.exists()


def test_real_pdf_cover_and_block_assets_are_generated_portably(tmp_path, monkeypatch):
    source_pdf = tmp_path / "visual.pdf"
    _make_pdf(source_pdf)
    monkeypatch.setattr(builder.shutil, "which", lambda _name: None)
    assets_root = tmp_path / "assets"

    cover = builder._generate_cover_asset(source_pdf, assets_root)
    blocks = builder._generate_missing_block_assets(
        source_pdf,
        [OcrBlock("figure-1", 1, "figure", [40, 50, 280, 180], text="diagram")],
        assets_root,
    )

    assert cover == "assets/cover/page_001.png"
    assert blocks[0].asset_path == "assets/generated/page_001_figure-1.png"
    with Image.open(tmp_path / cover), Image.open(tmp_path / blocks[0].asset_path) as block_image:
        assert block_image.width > 0
        assert block_image.height > 0
