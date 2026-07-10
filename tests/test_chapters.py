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


def test_build_chapters_splits_paper_top_level_sections_before_page_limit():
    blocks = [
        _heading("h_title", 1, "Impedance-Based Dynamics Analysis for DC-Link VSCs"),
        _paragraph("p_abstract", 1),
        _heading("h_intro", 1, "I. INTRODUCTION"),
        _paragraph("p_intro", 1),
        _heading("h_system", 2, "II. SYSTEM DESCRIPTION"),
        _paragraph("p_system", 2),
        _heading("h_subsection", 3, "A. Basic Principle of DC-Link Impedance-Based Analysis"),
        _paragraph("p_subsection", 3),
        _heading("h_analysis", 5, "III. DC-LINK IMPEDANCE-BASED DYNAMICS ANALYSIS"),
        _paragraph("p_analysis", 5),
    ]

    chapters = build_chapters(blocks)

    assert [chapter.title for chapter in chapters] == [
        "Impedance-Based Dynamics Analysis for DC-Link VSCs",
        "I. INTRODUCTION",
        "II. SYSTEM DESCRIPTION",
        "III. DC-LINK IMPEDANCE-BASED DYNAMICS ANALYSIS",
    ]
    assert [block.block_id for block in chapters[2].blocks] == [
        "h_system",
        "p_system",
        "h_subsection",
        "p_subsection",
    ]


def test_build_chapters_uses_first_heading_as_title_after_page_header_noise():
    blocks = [
        _paragraph("p_header", 1, "IEEE TRANSACTIONS"),
        _heading("h_title", 1, "Impedance-Based Dynamics Analysis for DC-Link VSCs"),
        _paragraph("p_abstract", 1),
        _heading("h_intro", 1, "I. INTRODUCTION"),
        _paragraph("p_intro", 1),
    ]

    chapters = build_chapters(blocks)

    assert [chapter.title for chapter in chapters] == [
        "Impedance-Based Dynamics Analysis for DC-Link VSCs",
        "I. INTRODUCTION",
    ]


def test_build_chapters_merges_short_chapter_label_into_following_title():
    blocks = [
        OcrBlock("label", 21, "unknown", [], text="CHAPTER 1"),
        _heading("h_ch1", 21, "BASIC CONCEPTS"),
        _paragraph("p_ch1", 21),
        _heading("h_ch2", 45, "NON-ISOLATED ZERO-VOLTAGE SWITCHING PWM CONVERTERS"),
        _paragraph("p_ch2", 45),
    ]

    chapters = build_chapters(blocks)

    assert [chapter.title for chapter in chapters] == [
        "BASIC CONCEPTS",
        "NON-ISOLATED ZERO-VOLTAGE SWITCHING PWM CONVERTERS",
    ]
    assert [block.block_id for block in chapters[0].blocks] == ["label", "h_ch1", "p_ch1"]


def test_build_chapters_repairs_common_dc_dc_title_spacing_glitches():
    blocks = [
        _heading("h_ch10", 194, "ZERO-VOLTAGE-ZERO-CURRENT SWITCHING DC-DC FULL-BRIDGEPWMCONVERTERS"),
        _paragraph("p_ch10", 194),
        _heading("h_ch11", 221, "ISOLATED CURRENT-FED DC-DC PWMCONVERTERS"),
        _paragraph("p_ch11", 221),
        _heading("h_ch12", 242, "RESONANT CONVERTERS PARTI-FUNDAMENTALS"),
        _paragraph("p_ch12", 242),
        _heading(
            "h_ch13",
            268,
            "RESONANT CONVERTERS PARTII– PWM CONTROLLED,QUASI-RESONANT,AND ULTRAHIGH-FREQUENCY CONVERTERS",
        ),
        _paragraph("p_ch13", 268),
    ]

    chapters = build_chapters(blocks)

    assert [chapter.title for chapter in chapters] == [
        "ZERO-VOLTAGE-ZERO-CURRENT SWITCHING DC-DC FULL-BRIDGE PWM CONVERTERS",
        "ISOLATED CURRENT-FED DC-DC PWM CONVERTERS",
        "RESONANT CONVERTERS PART I - FUNDAMENTALS",
        "RESONANT CONVERTERS PART II - PWM CONTROLLED, QUASI-RESONANT, AND ULTRAHIGH-FREQUENCY CONVERTERS",
    ]
    assert [chapter.blocks[0].block_id for chapter in chapters] == [
        "h_ch10",
        "h_ch11",
        "h_ch12",
        "h_ch13",
    ]


def test_build_chapters_splits_translated_paper_numbered_top_level_sections():
    blocks = [
        _heading("h_title", 1, "三相电压源逆变器的新型广义不连续SVPWM 策略研究"),
        _paragraph("p_abstract", 1),
        _heading("h_intro", 1, "1.引言"),
        _paragraph("p_intro", 1),
        _heading("h_principle", 1, "II. DSVPWMX的原理与实现"),
        _paragraph("p_principle", 1),
        _heading("h_subsection", 2, "1.1 参考电压"),
        _paragraph("p_subsection", 2),
        _heading("h_results", 6, "IV.仿真结果"),
        _paragraph("p_results", 6),
    ]

    chapters = build_chapters(blocks)

    assert [chapter.title for chapter in chapters] == [
        "三相电压源逆变器的新型广义不连续SVPWM 策略研究",
        "1.引言",
        "II. DSVPWMX的原理与实现",
        "IV.仿真结果",
    ]
    assert [block.block_id for block in chapters[2].blocks] == [
        "h_principle",
        "p_principle",
        "h_subsection",
        "p_subsection",
    ]
