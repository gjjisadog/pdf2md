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


def test_renderer_search_highlights_restore_original_block_html():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "node.dataset.originalHtml = node.innerHTML" in js
    assert "node.innerHTML = node.dataset.originalHtml" in js
    assert "delete node.dataset.originalHtml" in js
    assert "parent.replaceChildren(document.createTextNode(parent.textContent || \"\"))" not in js


def test_renderer_block_event_binding_is_idempotent_after_search_restore():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "if (node.dataset.blockEventsBound === \"true\") return" in js
    assert "node.dataset.blockEventsBound = \"true\"" in js
    assert "if (image.dataset.mediaEventsBound === \"true\") return" in js
    assert "image.dataset.mediaEventsBound = \"true\"" in js


def test_renderer_exposes_source_blocks_as_accessible_buttons():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert 'node.setAttribute("role", "button")' in js
    assert 'node.setAttribute("tabindex", "0")' in js
    assert 'node.setAttribute("aria-label", `source block ${blockId}`)' in js
    assert 'event.key === "Enter" || event.key === " "' in js


def test_renderer_delegates_source_block_touch_events_from_content_root():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "bindRootSourceMapEvents(root)" in js
    assert "root.dataset.sourceMapEventsBound === \"true\"" in js
    assert "document.elementFromPoint(touch.clientX, touch.clientY)" in js
    assert "target.closest(\"[data-block-id]\")" in js
    assert "Math.abs(touch.clientX - touchStartX) > 12" in js


def test_renderer_exposes_block_lookup_for_native_webview_taps():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "function blockIdAtPoint(x, y)" in js
    assert "document.elementFromPoint(x, y)" in js
    assert "blockIdAtPoint," in js


def test_renderer_supports_opt_in_native_source_links_for_ios_webview():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")
    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")

    assert "native_source_links" in js
    assert "installNativeSourceLink(node, blockId)" in js
    assert "bookmd-source://" in js
    assert "bookmd-source-link-overlay" in js
    assert ".bookmd-source-link-overlay" in css


def test_android_renderer_assets_match_package_renderer():
    package = Path("packages/markdown_renderer/renderer")
    android = Path("apps/reader-android/app/src/main/assets")

    for name in ["bookmd-renderer.html", "bookmd-renderer.css", "bookmd-renderer.js"]:
        assert (android / name).read_text(encoding="utf-8") == (
            package / name
        ).read_text(encoding="utf-8")


def test_renderer_supports_phase_four_markdown_features():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")
    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")

    assert "renderMarkdownTable" in js
    assert "renderCodeFence" in js
    assert "renderFootnote" in js
    assert "renderReferenceLink" in js
    assert "data-language-mode" in js
    assert "currentProgress" in js
    assert "restoreProgress" in js
    assert ".bookmd-code" in css
    assert ".bookmd-footnote" in css
    assert ".bookmd-table-scroll" in css


def test_renderer_sanitizes_reference_link_protocols_for_webview():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "sanitizeReferenceHref" in js
    assert "const safeHref = sanitizeReferenceHref(href)" in js
    assert "lower.startsWith(\"http://\") || lower.startsWith(\"https://\")" in js
    assert "value.startsWith(\"#\")" in js
    assert "!value.includes(\":\")" in js
    assert "data:" in js
    assert "intent:" in js
    assert "return \"#\"" in js
    assert "href=\"${escapeHtml(safeHref)}\"" in js


def test_renderer_optimizes_formula_table_and_image_blocks_for_mobile():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")
    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")

    assert 'class="bookmd-media-frame"' in js
    assert 'loading="lazy"' in js
    assert 'decoding="async"' in js
    assert ".bookmd-formula img" in js
    assert ".bookmd-media-frame" in css
    assert ".bookmd-formula .katex-display" in css
    assert "-webkit-overflow-scrolling: touch" in css
    assert "max-height: 72vh" in css
    assert "object-fit: contain" in css


def test_renderer_supports_paged_columns_swipe_and_page_progress():
    root = Path("packages/markdown_renderer/renderer")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")
    css = (root / "bookmd-renderer.css").read_text(encoding="utf-8")

    assert "column-width: calc(100vw - 40px)" in css
    assert "overflow-x: auto" in css
    assert "data-page-number" in css
    assert "setupPagination" in js
    assert "nextPage" in js
    assert "previousPage" in js
    assert "touchstart" in js
    assert "touchend" in js
    assert "page_index" in js
    assert "page_count" in js
    assert "onReadingProgressChangedPayload" in js
