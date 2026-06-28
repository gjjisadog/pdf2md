from converter.chapters import build_chapters
from source_map_core import OcrBlock


def _heading(block_id: str, page: int, text: str) -> OcrBlock:
    return OcrBlock(
        block_id=block_id,
        page=page,
        type="heading",
        bbox=[],
        text=text,
        level=1,
    )


def _paragraph(block_id: str, page: int, text: str = "Body") -> OcrBlock:
    return OcrBlock(block_id=block_id, page=page, type="paragraph", bbox=[], text=text)


def test_build_chapters_keeps_front_matter_noise_in_one_chapter():
    blocks = [
        _heading("h_title", 1, "DC-DC Converter Topologies Basic to Advanced"),
        _paragraph("p_title", 1),
        _heading("h_catalog", 6, "Library of Congress Cataloging-in-Publication Data applied for:"),
        _heading(
            "h_toc_late",
            12,
            "8VARIATIONS ON THE CONVENTIONAL ZERO-VOLTAGE SWITCHING DC-DC PWM FULL-BRIDGE CONVERTER",
        ),
        _heading("h_preface", 18, "PREFACE"),
        _heading("h_roman", 18, "xvi"),
        _heading("h_ch1", 21, "BASIC CONCEPTS"),
        _paragraph("p_ch1", 21),
    ]

    chapters = build_chapters(blocks)

    assert [chapter.title for chapter in chapters] == [
        "DC-DC Converter Topologies Basic to Advanced",
        "BASIC CONCEPTS",
    ]
    assert [block.block_id for block in chapters[0].blocks] == [
        "h_title",
        "p_title",
        "h_catalog",
        "h_toc_late",
        "h_preface",
        "h_roman",
    ]


def test_build_chapters_does_not_split_on_sections_references_or_index():
    blocks = [
        _heading("h_ch1", 21, "BASIC CONCEPTS"),
        _paragraph("p_ch1", 21),
        _heading("h_1_1", 22, "1.1 LINEAR VOLTAGE REGULATORS"),
        _paragraph("p_1_1", 22),
        _heading("h_refs", 43, "REFERENCES"),
        _paragraph("p_refs", 43),
        _heading("h_ch2", 45, "NON-ISOLATED ZERO-VOLTAGE SWITCHING PWM CONVERTERS"),
        _paragraph("p_ch2", 45),
        _heading("h_index", 450, "INDEX"),
        _paragraph("p_index", 450),
        _heading("h_license", 461, "WILEY eND USER LICENSE AGREEMENT"),
        _paragraph("p_license", 461),
    ]

    chapters = build_chapters(blocks)

    assert [chapter.title for chapter in chapters] == [
        "BASIC CONCEPTS",
        "NON-ISOLATED ZERO-VOLTAGE SWITCHING PWM CONVERTERS",
    ]
    assert [block.block_id for block in chapters[0].blocks] == [
        "h_ch1",
        "p_ch1",
        "h_1_1",
        "p_1_1",
        "h_refs",
        "p_refs",
    ]
