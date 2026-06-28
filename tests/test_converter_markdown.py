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
