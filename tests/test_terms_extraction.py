from translator_core import extract_terms


def test_extract_terms_finds_professional_terms_and_abbreviations():
    terms = extract_terms(
        [
            "The grid inverter uses a phase-locked loop (PLL).",
            "The proportional integral controller regulates the current controller.",
        ]
    )

    by_source = {item["source"]: item for item in terms}

    assert by_source["grid inverter"]["target"] == "并网逆变器"
    assert by_source["phase-locked loop"]["abbr"] == "PLL"
    assert by_source["phase-locked loop"]["target"] == "锁相环"
    assert by_source["proportional integral controller"]["category"] == "control"
