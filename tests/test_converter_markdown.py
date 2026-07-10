from converter.chapters import build_chapters
from converter.markdown import render_block_markdown
from source_map_core import OcrBlock


def test_render_paragraph_includes_hidden_trace_comment():
    block = OcrBlock(
        block_id="p001_b003",
        page=1,
        type="paragraph",
        bbox=[72, 188, 510, 246],
        text="并网逆变器通常采用电流内环控制。",
    )

    markdown = render_block_markdown(block)

    assert "<!-- block_id: p001_b003; page: 1; bbox: [72, 188, 510, 246] -->" in markdown
    assert "并网逆变器通常采用电流内环控制。" in markdown


def test_render_paragraph_repairs_obvious_ocr_spacing_glitches():
    block = OcrBlock(
        block_id="p001_b005",
        page=1,
        type="paragraph",
        bbox=[],
        text=(
            "In theinverter mode,the voltageynchronization method is used."
            "Astraightforwardwayisto add damping.Matrix.These results hold."
        ),
    )

    markdown = render_block_markdown(block)

    assert "the inverter mode, the voltage synchronization method" in markdown
    assert "A straightforward way is to add damping. Matrix. These results" in markdown
    assert "theinverter" not in markdown
    assert "mode,the" not in markdown
    assert "Matrix.These" not in markdown


def test_render_paragraph_repairs_toc_number_and_line_join_glitches():
    block = OcrBlock(
        block_id="p012_b004",
        page=12,
        type="paragraph",
        bbox=[],
        text=(
            "8.1Modified ZVS-PWM DC-DC Full-Bridge Converter with Saturable Reactors / 145\n"
            "8.1.1Modified ZVS-PWM-FB Converter with Primary-Side Saturable Reactor / 145"
            "8.1.2Modified ZVS-PWM-FB Converter with Secondary-Side Saturable Reactor / 146"
        ),
    )

    markdown = render_block_markdown(block)

    assert "8.1 Modified ZVS-PWM DC-DC Full-Bridge Converter" in markdown
    assert "8.1.1 Modified ZVS-PWM-FB Converter" in markdown
    assert "145 8.1.2 Modified ZVS-PWM-FB Converter" in markdown
    assert "145\n8.1.1" not in markdown
    assert "8.1Modified" not in markdown
    assert "8.1.1Modified" not in markdown


def test_render_paragraph_repairs_soft_hyphen_and_hyphenated_line_breaks():
    block = OcrBlock(
        block_id="p002_b001",
        page=2,
        type="paragraph",
        bbox=[],
        text="The soft\u00adhyphen should disappear and high-\nfrequency converters remain readable.",
    )

    markdown = render_block_markdown(block)

    assert "softhyphen" in markdown
    assert "high-frequency converters" in markdown
    assert "high-\nfrequency" not in markdown


def test_render_formula_prefers_latex():
    block = OcrBlock(
        block_id="eq_001",
        page=2,
        type="formula",
        bbox=[1, 2, 3, 4],
        latex="G_i(s)=K_p+\\frac{K_i}{s}",
    )

    markdown = render_block_markdown(block)

    assert "$$" in markdown
    assert "G_i(s)" in markdown


def test_render_formula_uses_text_latex_when_latex_field_is_missing():
    block = OcrBlock(
        block_id="eq_002",
        page=2,
        type="formula",
        bbox=[1, 2, 3, 4],
        text="\\begin{aligned}v_{a}^{*}=M\\cos(\\omega t)\\end{aligned}",
    )

    markdown = render_block_markdown(block)

    assert "$$" in markdown
    assert "\\begin{aligned}" in markdown
    assert ":::formula" not in markdown


def test_render_formula_with_asset_path_uses_visual_fallback():
    block = OcrBlock(
        block_id="eq_003",
        page=2,
        type="formula",
        bbox=[1, 2, 3, 4],
        text="V_{o}=D V_{in}",
        latex="V_{o}=D V_{in}",
        asset_path="assets/generated/page_002_eq_003.png",
    )

    markdown = render_block_markdown(block)

    assert ':::formula id="eq_003" src="../assets/generated/page_002_eq_003.png" page="2"' in markdown
    assert "V_{o}=D V_{in}" in markdown
    assert "$$" not in markdown


def test_render_figure_without_asset_path_falls_back_to_text():
    block = OcrBlock(
        block_id="fig_001",
        page=2,
        type="figure",
        bbox=[10, 20, 300, 420],
        text="Circuit diagram caption",
    )

    markdown = render_block_markdown(block)

    assert "Circuit diagram caption" in markdown
    assert ":::figure" not in markdown
    assert 'src="../"' not in markdown


def test_render_table_converts_ocr_html_table_to_markdown_table():
    block = OcrBlock(
        block_id="tbl_001",
        page=3,
        type="table",
        bbox=[1, 2, 3, 4],
        text=(
            "<html><body><table><tr><td>Type</td><td>Value</td></tr>"
            "<tr><td>$P_0$</td><td>3 kW</td></tr>"
            "<tr><td>Grid voltage</td><td>110 V</td></tr></table></body></html>"
        ),
    )

    markdown = render_block_markdown(block)

    assert "| Type | Value |" in markdown
    assert "| --- | --- |" in markdown
    assert "| $P_0$ | 3 kW |" in markdown
    assert "<html>" not in markdown
    assert ":::table" not in markdown


def test_render_table_converts_html_stored_in_markdown_field():
    block = OcrBlock(
        block_id="tbl_002",
        page=3,
        type="table",
        bbox=[1, 2, 3, 4],
        text="fallback",
        markdown="<html><body><table><tr><td>Name</td><td>Score</td></tr><tr><td>A</td><td>1</td></tr></table></body></html>",
    )

    markdown = render_block_markdown(block)

    assert "| Name | Score |" in markdown
    assert "| A | 1 |" in markdown
    assert "<table>" not in markdown


def test_render_table_with_asset_path_uses_visual_fallback():
    block = OcrBlock(
        block_id="tbl_003",
        page=3,
        type="table",
        bbox=[1, 2, 3, 4],
        text="<html><body><table><tr><td>Type</td></tr></table></body></html>",
        asset_path="assets/generated/page_003_tbl_003.png",
    )

    markdown = render_block_markdown(block)

    assert ':::table id="tbl_003" src="../assets/generated/page_003_tbl_003.png" page="3"' in markdown
    assert "Type" in markdown
    assert "<table>" not in markdown
    assert "| Type |" not in markdown


def test_build_chapters_splits_on_headings():
    blocks = [
        OcrBlock(
            block_id="h1",
            page=1,
            type="heading",
            bbox=[],
            text="第一章 绪论",
            level=1,
        ),
        OcrBlock(block_id="p1", page=1, type="paragraph", bbox=[], text="正文"),
    ]

    chapters = build_chapters(blocks)

    assert chapters[0].chapter_id == "ch_001"
    assert chapters[0].title == "第一章 绪论"
    assert chapters[0].path == "chapters/001_chapter_1.md"
