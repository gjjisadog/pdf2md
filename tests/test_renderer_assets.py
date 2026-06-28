from pathlib import Path


def test_renderer_assets_include_custom_block_hooks():
    root = Path("packages/markdown_renderer/renderer")

    html = (root / "bookmd-renderer.html").read_text(encoding="utf-8")
    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "bookmd-content" in html
    assert ".bookmd-figure" in css
    assert "window.BookMDReader" in js
    assert "block_id" in js
