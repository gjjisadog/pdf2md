from __future__ import annotations

from dataclasses import dataclass

from source_map_core import OcrBlock


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
        is_new_chapter = block.type == "heading" and (block.level or 1) <= 1
        if is_new_chapter and current_blocks:
            chapters.append(_make_chapter(len(chapters) + 1, current_title, current_blocks))
            current_blocks = []
        if is_new_chapter:
            current_title = block.text or f"Chapter {len(chapters) + 1}"
        current_blocks.append(block)

    if current_blocks:
        chapters.append(_make_chapter(len(chapters) + 1, current_title, current_blocks))

    if not chapters:
        chapters.append(_make_chapter(1, "Untitled", []))

    return chapters


def _make_chapter(order: int, title: str, blocks: list[OcrBlock]) -> Chapter:
    return Chapter(
        chapter_id=f"ch_{order:03d}",
        title=title,
        path=f"chapters/{order:03d}_chapter_{order}.md",
        order=order,
        blocks=list(blocks),
    )
