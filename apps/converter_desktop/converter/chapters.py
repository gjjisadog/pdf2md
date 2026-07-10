from __future__ import annotations

import re
from dataclasses import dataclass

from source_map_core import OcrBlock


FRONT_MATTER_PAGE_LIMIT = 20
IGNORED_HEADING_TITLES = {
    "ACKNOWLEDGMENTS",
    "ACKNOWLEDGEMENTS",
    "CONCLUSION",
    "CONCLUSIONS",
    "CONTENTS",
    "INDEX",
    "PREFACE",
    "REFERENCE",
    "REFERENCES",
    "TABLE OF CONTENTS",
}


@dataclass(frozen=True)
class Chapter:
    chapter_id: str
    title: str
    path: str
    order: int
    blocks: list[OcrBlock]


def build_chapters(blocks: list[OcrBlock]) -> list[Chapter]:
    chapters: list[Chapter] = []
    current_title = "Untitled"
    current_blocks: list[OcrBlock] = []

    for block in blocks:
        title = _clean_title(block.text)
        is_new_chapter = _is_chapter_heading(block, title)
        if is_new_chapter and current_blocks:
            if current_title != "Untitled" or not _is_chapter_label_prelude(current_blocks):
                chapters.append(_make_chapter(len(chapters) + 1, current_title, current_blocks))
                current_blocks = []
        if is_new_chapter:
            current_title = title or f"Chapter {len(chapters) + 1}"
        elif current_title == "Untitled" and block.type == "heading" and title:
            current_title = title
        current_blocks.append(block)

    if current_blocks:
        chapters.append(_make_chapter(len(chapters) + 1, current_title, current_blocks))

    if not chapters:
        chapters.append(_make_chapter(1, "Untitled", []))

    return chapters


def _is_chapter_heading(block: OcrBlock, title: str) -> bool:
    if block.type != "heading" or (block.level or 1) > 1:
        return False
    if not title or _is_ignored_heading(title):
        return False
    if _is_section_heading(title):
        return False
    if _is_explicit_chapter_heading(title):
        return True
    if _is_paper_top_level_heading(title):
        return True
    if _starts_with_glued_toc_number(title):
        return False
    if block.page <= FRONT_MATTER_PAGE_LIMIT:
        return False
    return _looks_like_main_heading(title)


def _clean_title(text: str) -> str:
    title = re.sub(r"\s+", " ", text).strip()
    title = title.replace("–", "-").replace("—", "-")
    title = re.sub(r"\bPART\s*I\s*-\s*", "PART I - ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bPART\s*II\s*-\s*", "PART II - ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bPARTI\s*-\s*", "PART I - ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bPARTII\s*-\s*", "PART II - ", title, flags=re.IGNORECASE)
    title = re.sub(r"(?i)BRIDGEPWM", "BRIDGE PWM", title)
    title = re.sub(r"(?i)\bPWMCONVERTERS\b", "PWM CONVERTERS", title)
    title = re.sub(r",(?=\S)", ", ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _is_ignored_heading(title: str) -> bool:
    upper = title.upper()
    if upper in IGNORED_HEADING_TITLES:
        return True
    if re.fullmatch(r"[ivxlcdm]+", title.strip(), flags=re.IGNORECASE):
        return True
    if "END USER LICENSE AGREEMENT" in upper:
        return True
    if "LIBRARY OF CONGRESS" in upper:
        return True
    return False


def _is_section_heading(title: str) -> bool:
    return bool(
        re.match(r"^(?:\d+|[A-Z])\.\d+(?:\.\d+)*\s*", title, flags=re.IGNORECASE)
    )


def _is_explicit_chapter_heading(title: str) -> bool:
    return bool(
        re.match(r"^(?:chapter\s+\d+|第\s*[一二三四五六七八九十百千\d]+\s*章)\b", title, flags=re.IGNORECASE)
    )


def _is_paper_top_level_heading(title: str) -> bool:
    return bool(
        re.match(r"^[IVX]+\.\s*\S+", title)
        or re.match(r"^\d+\.(?!\d)\s*\S+", title)
    )


def _starts_with_glued_toc_number(title: str) -> bool:
    return bool(re.match(r"^\d{1,3}[A-Za-z]", title))


def _looks_like_main_heading(title: str) -> bool:
    letters = [char for char in title if char.isalpha()]
    if len(letters) < 6:
        return False
    uppercase_letters = [char for char in letters if char.upper() == char]
    return len(uppercase_letters) / len(letters) >= 0.8


def _is_chapter_label_prelude(blocks: list[OcrBlock]) -> bool:
    if len(blocks) > 2:
        return False
    for block in blocks:
        title = _clean_title(block.text)
        if not re.fullmatch(r"(?:chapter\s+\d+|第\s*[一二三四五六七八九十百千\d]+\s*章)", title, flags=re.IGNORECASE):
            return False
    return bool(blocks)


def _make_chapter(order: int, title: str, blocks: list[OcrBlock]) -> Chapter:
    return Chapter(
        chapter_id=f"ch_{order:03d}",
        title=title,
        path=f"chapters/{order:03d}_chapter_{order}.md",
        order=order,
        blocks=list(blocks),
    )
