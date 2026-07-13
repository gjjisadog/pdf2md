from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader

from converter.pdf_backend import get_pdf_backend
from converter import ocr_pipeline


def _make_two_page_pdf(path: Path) -> None:
    pages: list[Image.Image] = []
    for color in ((25, 95, 180), (180, 75, 35)):
        image = Image.new("RGB", (320, 220), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 50, 280, 180), fill=color)
        pages.append(image)
    pages[0].save(path, "PDF", resolution=72.0, save_all=True, append_images=pages[1:])
    for image in pages:
        image.close()


def test_pdf_backend_counts_renders_and_crops_real_pdf(tmp_path):
    source_pdf = tmp_path / "source.pdf"
    _make_two_page_pdf(source_pdf)
    backend = get_pdf_backend()

    assert backend.page_count(source_pdf) == 2
    rendered = backend.render_page(source_pdf, 1, 144, tmp_path / "pages")
    cropped = tmp_path / "crop.png"

    assert rendered is not None
    assert rendered.exists()
    assert backend.crop_region(rendered, [40, 50, 280, 180], cropped)
    with Image.open(cropped) as image:
        assert image.width > 0
        assert image.height > 0
        assert any(pixel != (255, 255, 255) for pixel in image.convert("RGB").getdata())


def test_pdf_backend_splits_real_pdf_without_swift_or_system_tools(tmp_path):
    source_pdf = tmp_path / "source.pdf"
    _make_two_page_pdf(source_pdf)
    output = tmp_path / "split.pdf"
    backend = get_pdf_backend()

    result = backend.split_pages(source_pdf, 2, 1, output)

    assert result == output
    assert len(PdfReader(str(output)).pages) == 1


def test_pdf_backend_rejects_invalid_crop_bbox(tmp_path):
    image_path = tmp_path / "page.png"
    Image.new("RGB", (100, 100), "white").save(image_path)

    assert get_pdf_backend().crop_region(image_path, [10, 10, 10, 20], tmp_path / "crop.png") is False


def test_ocr_batch_split_routes_through_portable_backend(tmp_path, monkeypatch):
    calls: list[tuple[int, int, Path]] = []

    class FakeBackend:
        def page_count(self, _source_pdf: Path) -> int:
            return 5

        def split_pages(self, _source_pdf: Path, first_page: int, count: int, output: Path) -> Path:
            calls.append((first_page, count, output))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"pdf")
            return output

    monkeypatch.setattr(ocr_pipeline, "get_pdf_backend", lambda: FakeBackend())

    batches = ocr_pipeline.split_pdf_batches(
        tmp_path / "source.pdf",
        batch_size=2,
        work_dir=tmp_path / "batches",
    )

    assert [batch.first_page for batch in batches] == [1, 3, 5]
    assert [(first, count) for first, count, _ in calls] == [(1, 2), (3, 2), (5, 1)]
