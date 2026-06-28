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


def test_renderer_assets_include_markdown_and_custom_block_rendering_hooks():
    root = Path("packages/markdown_renderer/renderer")

    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "renderMarkdown" in js
    assert ":::figure" in js
    assert ":::formula" in js
    assert ":::table" in js
    assert ":::bilingual" in js
    assert "renderMathInElement" in js
    assert ".bookmd-bilingual" in css
    assert ".bookmd-footnote" in css


def test_renderer_assets_include_reader_interaction_hooks():
    root = Path("packages/markdown_renderer/renderer")

    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "jumpToBlock" in js
    assert "searchInChapter" in js
    assert "clearSearchHighlights" in js
    assert "onSourceMapRequested" in js
    assert "onImageSelected" in js
    assert ".bookmd-search-hit" in css
    assert ".bookmd-source-mark" in css
