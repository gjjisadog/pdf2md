#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SAMPLE = REPO / "tmp" / "real_book_full_clean_toc.bookmd"


def swift_sources() -> list[str]:
    sources = sorted((ROOT / "Sources" / "BookMDReaderCore").glob("*.swift"))
    return [str(path) for path in sources]


def snapshot_swift_sources(destination: Path) -> list[str]:
    source_snapshot = destination / "source_snapshot"
    source_snapshot.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in sorted((ROOT / "Sources" / "BookMDReaderCore").glob("*.swift")):
        target = source_snapshot / source.name
        shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile and optionally run BookMDReaderCore smoke checks.")
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Compile the generated Swift verifier without running it; useful when local Swift executables hang.",
    )
    args = parser.parse_args(argv)

    if not SAMPLE.exists():
        raise SystemExit(f"missing sample book: {SAMPLE}")

    with tempfile.TemporaryDirectory(prefix="bookmd-ios-core-") as tmp:
        tmp_path = Path(tmp)
        verifier = tmp_path / "VerifyBookMDReaderCore.swift"
        inflate_object = tmp_path / "BookMDZipInflate.o"
        binary = tmp_path / "verify-ios-core"
        source_snapshot = snapshot_swift_sources(tmp_path)
        verifier.write_text(
            f"""
import Foundation

func require(_ condition: @autoclosure () -> Bool, _ message: String) {{
    if !condition() {{
        FileHandle.standardError.write(Data("FAILED: \\(message)\\n".utf8))
        exit(1)
    }}
}}

func note(_ message: String) {{
    FileHandle.standardError.write(Data("[verify-ios-core] \\(message)\\n".utf8))
}}

@main
struct VerifyBookMDReaderCore {{
    static func main() throws {{
        let sample = URL(fileURLWithPath: "{SAMPLE}")
        note("validating archive")
        let validation = try BookMDArchiveValidator().validateArchive(at: sample)
        require(validation.isValid, "real book should validate")
        require(validation.manifest?.chapters.count == 18, "chapter count should be 18")

        note("opening archive")
        let archive = try BookMDArchive(url: sample)
        note("decoding manifest")
        let manifest = try archive.manifest()
        require(manifest.title == "DC-DC Converter Topologies Basic to Advanced", "title should decode")

        note("reading chapter markdown")
        let markdown = try archive.chapterMarkdown(path: "chapters/001_chapter_1.md")
        require(markdown.contains("p001_b001"), "chapter markdown should include block id")

        note("loading search index")
        let search = SearchService(items: try archive.searchIndex().items).search("Converter")
        require(!search.isEmpty, "search should find Converter")
        require(search.first?.blockId == "p001_b001", "search should preserve first jump block")

        note("loading source map")
        let sourceBlock = SourceMapIndex(blocks: try archive.sourceMap().blocks).block(for: "p001_b001")
        require(sourceBlock?.sourcePage == 1, "source map should preserve page")
        require(sourceBlock?.bbox == [164, 465, 864, 969], "source map should preserve bbox")

        note("persisting progress")
        let progressURL = URL(fileURLWithPath: "{tmp}").appendingPathComponent("progress.json")
        let store = try ReadingProgressStore(storageURL: progressURL)
        try store.save(ReadingProgress(
            bookId: manifest.bookId,
            chapterPath: "chapters/018_chapter_18.md",
            blockId: "p461_b002",
            scrollY: 2048,
            scrollX: 4096,
            pageIndex: 12,
            pageCount: 24,
            updatedAt: Date(timeIntervalSince1970: 1_800_000_000)
        ))
        let reloaded = try ReadingProgressStore(storageURL: progressURL)
        require(reloaded.progress(forBookId: manifest.bookId)?.blockId == "p461_b002", "book progress should reload")
        require(reloaded.progress(
            forBookId: manifest.bookId,
            chapterPath: "chapters/018_chapter_18.md"
        )?.scrollY == 2048, "chapter progress should reload")
        require(reloaded.progress(
            forBookId: manifest.bookId,
            chapterPath: "chapters/018_chapter_18.md"
        )?.scrollX == 4096, "paged scroll x should reload")
        require(reloaded.progress(
            forBookId: manifest.bookId,
            chapterPath: "chapters/018_chapter_18.md"
        )?.pageIndex == 12, "paged index should reload")
        require(reloaded.progress(
            forBookId: manifest.bookId,
            chapterPath: "chapters/018_chapter_18.md"
        )?.pageCount == 24, "paged count should reload")

        print("iOS core verification passed")
    }}
}}
""",
            encoding="utf-8",
        )

        subprocess.run(
            [
                "cc",
                "-I",
                str(ROOT / "Sources" / "BookMDReaderCore"),
                "-c",
                str(ROOT / "Sources" / "BookMDReaderCore" / "BookMDZipInflate.c"),
                "-o",
                str(inflate_object),
            ],
            cwd=ROOT,
            check=True,
            timeout=120,
        )

        command = [
            "swiftc",
            "-Onone",
            "-swift-version",
            "5",
            "-parse-as-library",
            "-import-objc-header",
            str(ROOT / "Sources" / "BookMDReaderCore" / "BookMDZipInflate.h"),
            *source_snapshot,
            str(verifier),
            str(inflate_object),
            "-lz",
            "-o",
            str(binary),
        ]
        subprocess.run(command, cwd=ROOT, check=True, timeout=120)
        if args.compile_only:
            print("iOS core compile verification passed")
            return 0
        try:
            subprocess.run([str(binary)], cwd=ROOT, check=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise SystemExit(
                "iOS core runtime verifier timed out while running the generated Swift binary. "
                "Use --compile-only until the local Swift runtime can launch compiled executables."
            ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
