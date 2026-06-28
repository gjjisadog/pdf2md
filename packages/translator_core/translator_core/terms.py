from __future__ import annotations

import re
from collections.abc import Iterable


_TERM_LEXICON: dict[str, tuple[str, str]] = {
    "grid inverter": ("并网逆变器", "power electronics"),
    "voltage source inverter": ("电压源逆变器", "power electronics"),
    "phase-locked loop": ("锁相环", "control"),
    "proportional integral controller": ("比例积分控制器", "control"),
    "current controller": ("电流控制器", "control"),
    "synchronous reference frame": ("同步参考坐标系", "control"),
    "pulse width modulation": ("脉宽调制", "power electronics"),
}


def extract_terms(texts: Iterable[str]) -> list[dict[str, str]]:
    joined = "\n".join(text for text in texts if text)
    lower_text = joined.lower()
    abbreviations = _find_abbreviations(joined)
    terms: list[dict[str, str]] = []

    for source, (target, category) in _TERM_LEXICON.items():
        if re.search(rf"\b{re.escape(source)}\b", lower_text):
            terms.append(
                {
                    "source": source,
                    "target": target,
                    "abbr": abbreviations.get(source, ""),
                    "category": category,
                    "note": "deterministic extractor",
                }
            )
    return terms


def _find_abbreviations(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in re.finditer(r"([A-Za-z][A-Za-z -]{2,80}?)\s*\(([A-Z][A-Z0-9]{1,12})\)", text):
        phrase = re.sub(r"\s+", " ", match.group(1).strip()).lower()
        abbr = match.group(2)
        for source in _TERM_LEXICON:
            if phrase.endswith(source):
                found[source] = abbr
    return found
