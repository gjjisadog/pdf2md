from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANDROID_PROJECT = ROOT / "apps/reader-android"
COMMON_ANDROID_SDKS = [
    Path("/opt/homebrew/share/android-commandlinetools"),
    Path.home() / "Library/Android/sdk",
    Path("/tmp/bookmd-android-sdk"),
]
PACKAGE_NAME = "com.bookmd.reader"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the Android BookMD reader.")
    parser.add_argument("--device-smoke", action="store_true", help="Run an optional connected-device smoke test.")
    parser.add_argument("--bookmd", type=Path, help="BookMD file to preload for --device-smoke.")
    parser.add_argument("--search-term", default="", help="Search term reserved for device smoke diagnostics.")
    parser.add_argument(
        "--import-via-picker",
        action="store_true",
        help="Use Android DocumentsUI to import --bookmd during --device-smoke instead of preloading app-private files.",
    )
    parser.add_argument("--verify-settings", action="store_true", help="Exercise Android reader settings during --device-smoke.")
    parser.add_argument("--verify-progress", action="store_true", help="Verify Android reading progress is persisted during --device-smoke.")
    parser.add_argument(
        "--verify-bad-import",
        action="store_true",
        help="Verify a corrupt .bookmd import fails visibly and preserves an existing shelf book.",
    )
    parser.add_argument(
        "--performance-baseline",
        action="store_true",
        help="Record coarse Android reader timing metrics to performance_baseline.json during --device-smoke.",
    )
    parser.add_argument(
        "--verify-visual-asset",
        action="store_true",
        help="Open the first real visual asset from --bookmd in ImageViewerActivity during --device-smoke.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=ROOT / "tmp/android_reader_verify",
        help="Directory for device-smoke failure screenshots, UI XML, dumpsys, and logcat.",
    )
    args = parser.parse_args(argv)

    checks = [
        [sys.executable, "scripts/sync_android_renderer_assets.py"],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_android_skeleton.py",
            "tests/test_renderer_assets.py",
        ],
    ]
    for command in checks:
        if _run(command, cwd=ROOT) != 0:
            return 1

    android_home = _android_home()
    if not android_home:
        print("FAILED: ANDROID_HOME or ANDROID_SDK_ROOT is required for assembleDebug")
        return 1
    if not _preflight_aapt2(android_home):
        return 1
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(android_home)
    env["ANDROID_SDK_ROOT"] = str(android_home)
    build_result = _run(
        _gradle_assemble_command(),
        cwd=ANDROID_PROJECT,
        env=env,
    )
    if build_result != 0:
        return build_result

    if args.device_smoke:
        if args.bookmd is None:
            print("FAILED: --bookmd is required with --device-smoke")
            return 1
        status = _device_smoke(
            android_home,
            args.bookmd,
            args.search_term,
            args.import_via_picker,
            args.verify_settings,
            args.verify_progress,
            args.verify_bad_import,
            args.performance_baseline,
            args.verify_visual_asset,
            args.artifacts_dir,
        )
        if status != 0:
            _collect_device_artifacts(android_home / "platform-tools" / "adb", args.artifacts_dir)
        return status

    return 0


def _android_home() -> Path | None:
    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(name)
        if value and (Path(value) / "platform-tools").exists():
            return Path(value)
    for candidate in COMMON_ANDROID_SDKS:
        if (candidate / "platform-tools").exists():
            return candidate
    return None


def _preflight_aapt2(android_home: Path, timeout_seconds: int = 5) -> bool:
    candidates = sorted((android_home / "build-tools").glob("*/aapt2"))
    if not candidates:
        print(f"WARNING: no SDK aapt2 found under {android_home / 'build-tools'}")
        print("Gradle may still download aapt2 from Maven during assembleDebug.")
        return True

    failures = []
    for candidate in candidates:
        try:
            completed = subprocess.run(
                [str(candidate), "version"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            failures.append(f"{candidate}: timed out after {timeout_seconds}s")
            continue
        if completed.returncode == 0:
            version = completed.stdout.strip() or "version output was empty"
            print(f"Android aapt2 preflight passed: {candidate} ({version})")
            return True
        reason = (completed.stderr or completed.stdout).strip() or f"exit {completed.returncode}"
        failures.append(f"{candidate}: {reason}")

    print("FAILED: Android aapt2 cannot start from installed build-tools.")
    for failure in failures:
        print(f"  - {failure}")
    print(
        "Fix: run sdkmanager with JDK 17+ to reinstall build-tools, or run the "
        "Android verification on a Linux/Docker/CI host if macOS keeps hanging."
    )
    print(
        "Note: Gradle's Maven-provided aapt2 may fail the same way when the "
        "local macOS process loader/dyld cannot start aapt2 binaries."
    )
    return False


def _gradle_assemble_command() -> list[str]:
    return ["sh", str(ANDROID_PROJECT / "gradlew"), ":app:assembleDebug"]


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> int:
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd, text=True, env=env, check=False)
    if completed.returncode != 0:
        print(f"FAILED: {' '.join(command)}")
    return completed.returncode


def _device_smoke(
    android_home: Path,
    bookmd: Path,
    search_term: str,
    import_via_picker: bool = False,
    verify_settings: bool = False,
    verify_progress: bool = False,
    verify_bad_import: bool = False,
    performance_baseline: bool = False,
    verify_visual_asset: bool = False,
    artifacts_dir: Path | None = None,
) -> int:
    if not bookmd.exists():
        print(f"FAILED: BookMD file does not exist: {bookmd}")
        return 1
    adb = android_home / "platform-tools" / "adb"
    apk = ANDROID_PROJECT / "app/build/outputs/apk/debug/app-debug.apk"
    remote_book = (
        f"/sdcard/Download/{_device_file_name(bookmd)}"
        if import_via_picker
        else f"/data/local/tmp/{_device_file_name(bookmd)}"
    )
    remote_name = Path(remote_book).name
    book_dir = Path(remote_name).stem
    performance: dict[str, float | str] = {}
    total_started = time.perf_counter()

    if not _assert_device_connected(adb):
        return 1

    commands = [[str(adb), "install", "-r", str(apk)]]
    if import_via_picker:
        commands.extend(
            [
                [str(adb), "shell", "mkdir", "-p", "/sdcard/Download"],
                [str(adb), "push", str(bookmd), remote_book],
                [str(adb), "shell", "pm", "clear", PACKAGE_NAME],
            ]
        )
    else:
        commands.extend(
            [
                [str(adb), "shell", "pm", "clear", PACKAGE_NAME],
                [str(adb), "push", str(bookmd), remote_book],
                [str(adb), "shell", "chmod", "644", remote_book],
                [
                    str(adb),
                    "shell",
                    _run_as_shell_command(
                        f"mkdir -p files && "
                        f"rm -rf files/{book_dir} files/{remote_name} && "
                        f"cp {remote_book} files/{remote_name} && "
                        f"mkdir -p files/{book_dir} && "
                        f"cd files/{book_dir} && unzip -oq ../{remote_name}"
                    ),
                ],
            ]
        )
    commands.extend(
        [
            [str(adb), "shell", "am", "force-stop", "com.google.android.documentsui"],
            [str(adb), "shell", "am", "force-stop", PACKAGE_NAME],
            [str(adb), "shell", "am", "start", "-S", "-n", f"{PACKAGE_NAME}/.BookShelfActivity"],
        ]
    )
    setup_started = time.perf_counter()
    for command in commands:
        if _adb(command).returncode != 0:
            print(f"FAILED: {' '.join(command)}")
            return 1

    if not _assert_app_running(adb):
        return 1
    if not _assert_bookmd_focus(adb):
        return 1
    _record_performance_ms(performance, "setup_and_shelf_ready_ms", setup_started)

    title = _book_title(bookmd)
    if import_via_picker and not _import_book_via_picker(adb, remote_name, title):
        return 1
    existing_title = title
    if verify_bad_import and not _verify_bad_import_via_picker(adb, existing_title):
        return 1

    node = _find_book_node_on_shelf(adb, title) if title else None
    if node is None:
        xml = _dump_ui_xml(adb)
        node = _first_clickable_text_node(xml, excluded_texts={"IMPORT .BOOKMD", "LOGS", "DELETE"})
    if node is None:
        print("FAILED: no clickable book node found on Android shelf")
        return 1
    open_started = time.perf_counter()
    if not _tap_node(adb, node):
        print("FAILED: unable to tap first book node")
        return 1

    book_activity = _wait_for_book_open_activity(adb)
    if book_activity is None:
        print("FAILED: Android reader did not open a TOC or reader activity")
        return 1
    xml = _wait_for_ui(
        adb,
        lambda current: "android.webkit.WebView" in current if book_activity == "ReaderActivity" else _toc_visible(current),
    )
    chapter = None
    if "android.webkit.WebView" not in xml:
        chapter = _chapter_node(xml)
    if chapter is not None and not _tap_node(adb, chapter):
        print("FAILED: unable to tap first chapter node")
        return 1
    if chapter is not None and not _wait_for_bookmd_activity_focus(adb, "ReaderActivity"):
        print("FAILED: chapter tap did not open Android reader")
        return 1

    xml = _wait_for_ui(adb, lambda current: "android.webkit.WebView" in current)
    if "android.webkit.WebView" not in xml:
        print("FAILED: reader page did not expose a WebView")
        return 1
    _record_performance_ms(performance, "open_to_reader_ms", open_started)

    if verify_settings:
        settings_started = time.perf_counter()
        if not _verify_settings_flow(adb, xml):
            return 1
        xml = _wait_for_ui(adb, lambda current: "android.webkit.WebView" in current)
        _record_performance_ms(performance, "settings_round_trip_ms", settings_started)

    if verify_progress:
        progress_started = time.perf_counter()
        _adb([str(adb), "shell", "input", "swipe", "540", "1500", "540", "600"])
        time.sleep(1.0)
        if not _progress_saved(adb, book_dir):
            print("FAILED: Android reading progress was not persisted")
            return 1
        restored_xml = _restore_progress_from_shelf(adb, title)
        if "android.webkit.WebView" not in restored_xml:
            print("FAILED: Android reading progress did not restore to reader")
            return 1
        xml = restored_xml
        _record_performance_ms(performance, "progress_restore_ms", progress_started)

    if verify_visual_asset:
        visual_started = time.perf_counter()
        if not _verify_visual_asset_flow(adb, bookmd, book_dir):
            return 1
        xml = _wait_for_ui(adb, lambda current: "android.webkit.WebView" in current)
        _record_performance_ms(performance, "visual_asset_viewer_ms", visual_started)

    if search_term:
        search_started = time.perf_counter()
        if not _verify_search_flow(adb, xml, search_term):
            return 1
        xml = _wait_for_ui(adb, lambda current: "android.webkit.WebView" in current)
        _record_performance_ms(performance, "search_flow_ms", search_started)

    source_started = time.perf_counter()
    if not _tap_source_block(adb, xml):
        print("FAILED: unable to tap source-mapped reader content")
        return 1
    xml = _wait_for_ui(
        adb,
        lambda current: _source_dialog_visible(current) or _source_page_visible(adb, current),
        attempts=40,
    )
    if _source_page_visible(adb, xml):
        _record_performance_ms(performance, "source_trace_ms", source_started)
        _record_performance_ms(performance, "total_smoke_ms", total_started)
        if performance_baseline:
            _write_performance_baseline(artifacts_dir, performance)
        return 0
    if not _source_dialog_visible(xml):
        print("FAILED: source map dialog did not open")
        return 1
    open_pdf = _node_by_text(xml, "OPEN PDF PAGE")
    if open_pdf is None or not _tap_node(adb, open_pdf):
        print("FAILED: source map dialog did not expose Open PDF Page")
        return 1
    xml = _wait_for_ui(adb, lambda current: _source_page_visible(adb, current))
    if not _source_page_visible(adb, xml):
        print("FAILED: source PDF page did not render")
        return 1
    _record_performance_ms(performance, "source_trace_ms", source_started)
    _record_performance_ms(performance, "total_smoke_ms", total_started)
    if performance_baseline:
        _write_performance_baseline(artifacts_dir, performance)
    return 0


def _record_performance_ms(performance: dict[str, float | str], name: str, started_at: float) -> None:
    performance[name] = round((time.perf_counter() - started_at) * 1000, 1)


def _write_performance_baseline(artifacts_dir: Path | None, performance: dict[str, float | str]) -> None:
    target_dir = artifacts_dir or (ROOT / "tmp/android_reader_verify")
    target_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "android_reader_performance_baseline_v1",
        "metrics": performance,
    }
    (target_dir / "performance_baseline.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _adb(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(
            command,
            124,
            error.stdout or "",
            f"adb command timed out after {error.timeout}s",
        )


def _adb_binary(command: list[str]) -> bytes:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=False, timeout=30)
    return result.stdout if isinstance(result.stdout, bytes) else result.stdout.encode("latin1", errors="ignore")


def _collect_device_artifacts(adb: Path, artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    _adb([str(adb), "shell", "uiautomator", "dump", "/sdcard/window.xml"])
    window = _adb([str(adb), "shell", "cat", "/sdcard/window.xml"])
    (artifacts_dir / "window.xml").write_text(window.stdout, encoding="utf-8")
    focus = _adb([str(adb), "shell", "dumpsys", "activity", "activities"])
    (artifacts_dir / "window_focus.txt").write_text(focus.stdout, encoding="utf-8")
    logcat = _adb([str(adb), "logcat", "-d", "-t", "300"])
    (artifacts_dir / "logcat_tail.txt").write_text(logcat.stdout, encoding="utf-8")
    screenshot_payload = _adb_binary([str(adb), "exec-out", "screencap", "-p"])
    (artifacts_dir / "screenshot.png").write_bytes(screenshot_payload)


def _dump_ui_xml(adb: Path) -> str:
    try:
        subprocess.run(
            [str(adb), "shell", "uiautomator", "dump", "/sdcard/window.xml"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
        result = subprocess.run(
            [str(adb), "shell", "cat", "/sdcard/window.xml"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except subprocess.TimeoutExpired:
        return ""
    return result.stdout


def _wait_for_ui(adb: Path, predicate, attempts: int = 20, delay: float = 0.5) -> str:
    last_xml = ""
    for _attempt in range(attempts):
        last_xml = _dump_ui_xml(adb)
        if predicate(last_xml):
            return last_xml
        time.sleep(delay)
    return last_xml


def _import_book_via_picker(adb: Path, remote_name: str, title: str) -> bool:
    xml = _wait_for_ui(adb, lambda current: _node_by_text_casefold(current, "Import .bookmd") is not None)
    import_button = _node_by_text_casefold(xml, "Import .bookmd")
    if import_button is None or not _tap_node(adb, import_button):
        print("FAILED: Android shelf did not expose Import .bookmd")
        return False

    if not _wait_for_bookmd_activity_focus(adb, "BookImportActivity"):
        print("FAILED: Android import screen did not receive focus")
        return False
    xml = _wait_for_ui(adb, lambda current: _node_by_text_casefold(current, "Import .bookmd") is not None)
    import_button = _node_by_text_casefold(xml, "Import .bookmd")
    if import_button is None or not _tap_node(adb, import_button):
        print("FAILED: Android import screen did not expose Import .bookmd")
        return False

    document = _find_document_node_in_picker(adb, remote_name)
    if document is None or not _tap_node(adb, document):
        print(f"FAILED: DocumentsUI did not expose {remote_name}")
        return False

    imported_xml = _wait_for_ui(
        adb,
        lambda current: "Imported:" in current or (bool(title) and title in current),
        attempts=60,
    )
    if "Imported:" not in imported_xml and (not title or title not in imported_xml):
        print("FAILED: selected BookMD was not imported")
        return False

    if _bookmd_activity_has_focus(adb, "BookImportActivity"):
        if _adb([str(adb), "shell", "input", "keyevent", "4"]).returncode != 0:
            print("FAILED: unable to return from import screen to shelf")
            return False
    if not _assert_bookmd_focus(adb):
        return False
    return True


def _verify_bad_import_via_picker(adb: Path, existing_title: str) -> bool:
    bad_bookmd = _write_corrupt_bookmd()
    remote_name = "CorruptBookmdSmoke.bookmd"
    remote_book = f"/sdcard/Download/{remote_name}"
    if _adb([str(adb), "shell", "mkdir", "-p", "/sdcard/Download"]).returncode != 0:
        print("FAILED: unable to prepare Downloads for corrupt BookMD smoke")
        return False
    if _adb([str(adb), "push", str(bad_bookmd), remote_book]).returncode != 0:
        print("FAILED: unable to push corrupt BookMD smoke file")
        return False
    if _adb([str(adb), "shell", "am", "start", "-n", f"{PACKAGE_NAME}/.BookShelfActivity"]).returncode != 0:
        print("FAILED: unable to return to shelf before corrupt import smoke")
        return False
    if not _assert_bookmd_focus(adb):
        return False

    xml = _wait_for_ui(adb, lambda current: _node_by_text_casefold(current, "Import .bookmd") is not None)
    import_button = _node_by_text_casefold(xml, "Import .bookmd")
    if import_button is None or not _tap_node(adb, import_button):
        print("FAILED: Android shelf did not expose Import .bookmd for corrupt import smoke")
        return False

    if not _wait_for_bookmd_activity_focus(adb, "BookImportActivity"):
        print("FAILED: Android import screen did not receive focus for corrupt import smoke")
        return False
    xml = _wait_for_ui(adb, lambda current: _node_by_text_casefold(current, "Import .bookmd") is not None)
    import_button = _node_by_text_casefold(xml, "Import .bookmd")
    if import_button is None or not _tap_node(adb, import_button):
        print("FAILED: Android import screen did not expose Import .bookmd for corrupt import smoke")
        return False

    document = _find_document_node_in_picker(adb, remote_name)
    if document is None or not _tap_node(adb, document):
        print(f"FAILED: DocumentsUI did not expose {remote_name}")
        return False

    failed_xml = _wait_for_ui(adb, lambda current: "Import failed:" in current, attempts=60)
    if "Import failed:" not in failed_xml:
        print("FAILED: corrupt BookMD import did not show Import failed")
        return False
    if existing_title and _find_book_node_on_shelf_from_import_screen(adb, existing_title) is None:
        print("FAILED: existing shelf book was not visible after corrupt import failed")
        return False
    return True


def _find_book_node_on_shelf_from_import_screen(adb: Path, existing_title: str) -> dict[str, str] | None:
    if _adb([str(adb), "shell", "input", "keyevent", "4"]).returncode != 0:
        return None
    if not _assert_bookmd_focus(adb):
        return None
    return _find_book_node_on_shelf(adb, existing_title)


def _write_corrupt_bookmd() -> Path:
    target = ROOT / "tmp/android_reader_verify_bad_import/CorruptBookmdSmoke.bookmd"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"this is not a valid bookmd zip\n")
    return target


def _first_clickable_text_node(xml: str, excluded_texts: set[str]) -> dict[str, str] | None:
    excluded = {item.casefold() for item in excluded_texts}
    for node in _iter_ui_nodes(xml):
        text = node.get("text", "").strip()
        bounds = node.get("bounds", "")
        if node.get("clickable") != "true" or not text or not bounds:
            continue
        if text.casefold() in excluded:
            continue
        return node
    return None


def _first_visual_asset_reference(bookmd: Path) -> str | None:
    try:
        with zipfile.ZipFile(bookmd) as archive:
            names = set(archive.namelist())
            generated: list[str] = []
            fallback: list[str] = []
            for name in sorted(names):
                if not name.startswith("chapters/") or not name.endswith(".md"):
                    continue
                chapter_text = archive.read(name).decode("utf-8", errors="replace")
                for reference in _asset_references_from_markdown(chapter_text):
                    if reference not in names:
                        continue
                    if reference.startswith("assets/cover/"):
                        continue
                    if reference.startswith("assets/generated/"):
                        generated.append(reference)
                    elif reference.startswith("assets/"):
                        fallback.append(reference)
            return (generated or fallback or [None])[0]
    except (OSError, zipfile.BadZipFile, KeyError):
        return None


def _asset_references_from_markdown(markdown: str) -> list[str]:
    references: list[str] = []
    for match in re.finditer(r"""src\s*=\s*["']\.\./(assets/[^"']+)["']""", markdown):
        references.append(match.group(1))
    for match in re.finditer(r"""!\[[^\]]*]\(\.\./(assets/[^)\s]+)\)""", markdown):
        references.append(match.group(1))
    return references


def _verify_visual_asset_flow(adb: Path, bookmd: Path, book_dir: str) -> bool:
    asset_reference = _first_visual_asset_reference(bookmd)
    if not asset_reference:
        print("FAILED: BookMD has no referenced visual asset to smoke-test")
        return False
    device_book_dir = f"/data/data/{PACKAGE_NAME}/files/{book_dir}"
    media_uri = f"file://{device_book_dir}/{asset_reference}"
    if _adb(
        [
            str(adb),
            "shell",
            "am",
            "start",
            "-n",
            f"{PACKAGE_NAME}/.BookShelfActivity",
            "--activity-clear-top",
            "--activity-single-top",
            "--ez",
            "smoke_visual_asset",
            "true",
            "--es",
            "book_dir",
            device_book_dir,
            "--es",
            "media_uri",
            media_uri,
        ]
    ).returncode != 0:
        print("FAILED: unable to launch ImageViewerActivity for visual asset")
        return False
    if not _wait_for_bookmd_activity_focus(adb, "ImageViewerActivity"):
        print("FAILED: visual asset did not open ImageViewerActivity")
        return False
    xml = _wait_for_ui(adb, lambda current: "android.webkit.WebView" in current, attempts=10)
    if "android.webkit.WebView" not in xml:
        print("FAILED: visual asset viewer did not expose a WebView")
        return False
    if _adb([str(adb), "shell", "input", "keyevent", "4"]).returncode != 0:
        print("FAILED: unable to return from visual asset viewer")
        return False
    if not _wait_for_bookmd_activity_focus(adb, "ReaderActivity"):
        restored_xml = _restore_progress_from_shelf(adb, _book_title(bookmd))
        if "android.webkit.WebView" not in restored_xml:
            print("FAILED: visual asset viewer did not return to reader")
            return False
    return True


def _chapter_node(xml: str) -> dict[str, str] | None:
    return _first_clickable_text_node(
        xml,
        excluded_texts={"TOC", "PREV", "NEXT", "SEARCH", "SETTINGS", "IMPORT .BOOKMD", "LOGS", "DELETE"},
    )


def _toc_visible(xml: str) -> bool:
    return (
        _node_by_text_casefold(xml, "Search") is not None
        and _node_by_text_casefold(xml, "Settings") is not None
        and _chapter_node(xml) is not None
    )


def _node_by_text_casefold(xml: str, text: str) -> dict[str, str] | None:
    target = text.casefold()
    for node in _iter_ui_nodes(xml):
        if node.get("text", "").casefold() == target and node.get("bounds"):
            return node
    return None


def _node_by_text(xml: str, text: str) -> dict[str, str] | None:
    for node in _iter_ui_nodes(xml):
        if node.get("text") == text and node.get("bounds"):
            return node
    return None


def _node_by_class(xml: str, class_name: str) -> dict[str, str] | None:
    for node in _iter_ui_nodes(xml):
        if node.get("class") == class_name and node.get("bounds"):
            return node
    return None


def _source_dialog_visible(xml: str) -> bool:
    return "Source:" in xml or _node_by_text(xml, "OPEN PDF PAGE") is not None


def _source_page_visible(adb: Path, xml: str) -> bool:
    return "Page " in xml or _bookmd_activity_has_focus(adb, "SourcePageActivity")


def _iter_ui_nodes(xml: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    return [dict(node.attrib) for node in root.iter("node")]


def _center_of_bounds(bounds: str) -> tuple[int, int]:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if not match:
        raise ValueError(f"invalid Android UI bounds: {bounds}")
    left, top, right, bottom = (int(value) for value in match.groups())
    return ((left + right) // 2, (top + bottom) // 2)


def _device_file_name(bookmd: Path) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", bookmd.name).strip("._")
    return safe or "sample.bookmd"


def _book_title(bookmd: Path) -> str:
    try:
        with zipfile.ZipFile(bookmd) as archive:
            data = json.loads(archive.read("book.json"))
    except (KeyError, OSError, json.JSONDecodeError, zipfile.BadZipFile):
        return ""
    title = data.get("title", "")
    return title if isinstance(title, str) else ""


def _find_book_node_on_shelf(adb: Path, title: str, attempts: int = 6) -> dict[str, str] | None:
    for attempt in range(attempts):
        xml = _dump_ui_xml(adb)
        node = _node_by_text(xml, title)
        if node is not None:
            return node
        if attempt < attempts - 1:
            _adb([str(adb), "shell", "input", "swipe", "540", "1650", "540", "500"])
            time.sleep(0.25)
    return None


def _find_document_node_in_picker(adb: Path, file_name: str, attempts: int = 8) -> dict[str, str] | None:
    for attempt in range(attempts):
        xml = _dump_ui_xml(adb)
        node = _document_node(xml, file_name)
        if node is not None:
            return node
        if attempt < attempts - 1:
            _adb([str(adb), "shell", "input", "swipe", "540", "1650", "540", "500"])
            time.sleep(0.25)
    if not _open_downloads_in_picker(adb):
        return None
    for attempt in range(max(1, attempts)):
        xml = _dump_ui_xml(adb)
        node = _document_node(xml, file_name)
        if node is not None:
            return node
        if attempt < attempts - 1:
            _adb([str(adb), "shell", "input", "swipe", "540", "1650", "540", "500"])
            time.sleep(0.25)
    return None


def _document_node(xml: str, file_name: str) -> dict[str, str] | None:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    return _find_text_node_or_clickable_ancestor(root, file_name, [])


def _find_text_node_or_clickable_ancestor(
    element: ET.Element,
    text: str,
    ancestors: list[ET.Element],
) -> dict[str, str] | None:
    if element.attrib.get("text") == text and element.attrib.get("bounds"):
        if element.attrib.get("clickable") == "true":
            return dict(element.attrib)
        for ancestor in reversed(ancestors):
            if ancestor.attrib.get("clickable") == "true" and ancestor.attrib.get("bounds"):
                return dict(ancestor.attrib)
        return dict(element.attrib)
    for child in list(element):
        node = _find_text_node_or_clickable_ancestor(child, text, [*ancestors, element])
        if node is not None:
            return node
    return None


def _open_downloads_in_picker(adb: Path) -> bool:
    xml = _wait_for_ui(adb, lambda current: _node_by_content_desc(current, "Show roots") is not None, attempts=3)
    roots = _node_by_content_desc(xml, "Show roots")
    if roots is None or not _tap_node(adb, roots):
        return False
    xml = _wait_for_ui(adb, lambda current: _node_by_text_casefold(current, "Downloads") is not None, attempts=5)
    downloads = _node_by_text_casefold(xml, "Downloads")
    return downloads is not None and _tap_node(adb, downloads)


def _node_by_content_desc(xml: str, content_desc: str) -> dict[str, str] | None:
    for node in _iter_ui_nodes(xml):
        if node.get("content-desc") == content_desc and node.get("bounds"):
            return node
    return None


def _run_as_shell_command(script: str) -> str:
    return f"run-as {PACKAGE_NAME} /system/bin/sh -c {shlex.quote(script)}"


def _assert_app_running(adb: Path) -> bool:
    for _attempt in range(20):
        result = _adb([str(adb), "shell", "pidof", PACKAGE_NAME])
        if result.returncode == 0 and result.stdout.strip():
            return True
        time.sleep(0.5)
    print("FAILED: Android reader process is not running")
    return False


def _assert_device_connected(adb: Path) -> bool:
    result = _adb([str(adb), "devices"])
    if result.returncode != 0:
        print("FAILED: adb devices failed")
        return False
    device_lines = [
        line
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("List of devices")
    ]
    if any(line.split()[1:2] == ["device"] for line in device_lines):
        return True
    print("FAILED: no connected Android device or emulator for --device-smoke")
    return False


def _assert_bookmd_focus(adb: Path) -> bool:
    for _attempt in range(20):
        for command in (
            [str(adb), "shell", "dumpsys", "activity", "activities"],
            [str(adb), "shell", "dumpsys", "window"],
        ):
            result = _adb(command)
            if result.returncode == 0 and _bookmd_has_focus(result.stdout):
                return True
        time.sleep(0.5)
    print("FAILED: Android reader window is not focused")
    return False


def _bookmd_has_focus(dumpsys_output: str) -> bool:
    focus_markers = ("mCurrentFocus", "mFocusedApp")
    return any(
        PACKAGE_NAME in line and any(marker in line for marker in focus_markers)
        for line in dumpsys_output.splitlines()
    )


def _bookmd_activity_has_focus(adb: Path, activity_name: str) -> bool:
    focus_markers = ("topResumedActivity", "mCurrentFocus", "mFocusedApp")
    for command in (
        [str(adb), "shell", "dumpsys", "activity", "activities"],
        [str(adb), "shell", "dumpsys", "window"],
    ):
        result = _adb(command)
        if result.returncode != 0:
            continue
        if any(
            PACKAGE_NAME in line
            and activity_name in line
            and any(marker in line for marker in focus_markers)
            for line in result.stdout.splitlines()
        ):
            return True
    return False


def _wait_for_bookmd_activity_focus(adb: Path, activity_name: str, attempts: int = 20) -> bool:
    for _attempt in range(attempts):
        if _bookmd_activity_has_focus(adb, activity_name):
            return True
        time.sleep(0.5)
    return False


def _wait_for_book_open_activity(adb: Path, attempts: int = 20) -> str | None:
    for _attempt in range(attempts):
        for activity_name in ("TocActivity", "ReaderActivity"):
            if _bookmd_activity_has_focus(adb, activity_name):
                return activity_name
        time.sleep(0.5)
    return None


def _tap_node(adb: Path, node: dict[str, str]) -> bool:
    x, y = _center_of_bounds(node["bounds"])
    return _adb([str(adb), "shell", "input", "tap", str(x), str(y)]).returncode == 0


def _verify_search_flow(adb: Path, reader_xml: str, search_term: str) -> bool:
    search_button = _node_by_text(reader_xml, "Search") or _node_by_text(reader_xml, "SEARCH")
    if search_button is None or not _tap_node(adb, search_button):
        print("FAILED: reader Search button was not found")
        return False
    if not _enter_search_term(adb, search_term):
        print(f"FAILED: search field did not contain {search_term!r}")
        return False
    search_xml = _wait_for_ui(
        adb,
        lambda current: _node_by_text(current, "SEARCH") is not None or _node_by_text(current, "Search") is not None,
    )
    submit = _node_by_text(search_xml, "SEARCH") or _node_by_text(search_xml, "Search")
    if submit is None or not _tap_node(adb, submit):
        print("FAILED: search submit button was not found")
        return False
    results_xml = _wait_for_ui(adb, lambda current: _search_results_ready(current, search_term))
    if _node_by_text(results_xml, "No results.") is not None:
        print(f"FAILED: search returned no results for {search_term!r}")
        return False
    if search_term.casefold() not in results_xml.casefold():
        print(f"FAILED: search results did not contain {search_term!r}")
        return False
    result = _search_result_node(results_xml)
    if result is None or not _tap_node(adb, result):
        print("FAILED: no tappable search result was found")
        return False
    return True


def _search_results_ready(xml: str, search_term: str) -> bool:
    if _node_by_text(xml, "No results.") is not None:
        return True
    result = _search_result_node(xml)
    if result is None:
        return False
    return search_term.casefold() in result.get("text", "").casefold()


def _enter_search_term(adb: Path, search_term: str, attempts: int = 3) -> bool:
    search_xml = _wait_for_ui(adb, lambda current: _search_input_node(current) is not None)
    input_node = _search_input_node(search_xml)
    if input_node is None or not _tap_node(adb, input_node):
        return False
    current_text = input_node.get("text", "")
    for attempt in range(attempts):
        if current_text:
            _adb([str(adb), "shell", "input", "keyevent", "123"])
            for _ in range(len(current_text)):
                _adb([str(adb), "shell", "input", "keyevent", "67"])
        if _adb([str(adb), "shell", "input", "text", _adb_input_text(search_term)]).returncode != 0:
            return False
        typed_xml = _wait_for_ui(
            adb,
            lambda current: _search_input_text(current) == search_term,
            attempts=6,
            delay=0.25,
        )
        current_text = _search_input_text(typed_xml)
        if current_text == search_term:
            return True
        if attempt < attempts - 1:
            time.sleep(0.25)
    return False


def _search_input_node(xml: str) -> dict[str, str] | None:
    return _node_by_class(xml, "android.widget.EditText")


def _search_input_text(xml: str) -> str:
    node = _search_input_node(xml)
    return node.get("text", "") if node else ""


def _verify_settings_flow(adb: Path, reader_xml: str) -> bool:
    settings_button = _node_by_text(reader_xml, "Settings") or _node_by_text(reader_xml, "SETTINGS")
    if settings_button is None or not _tap_node(adb, settings_button):
        print("FAILED: reader Settings button was not found")
        return False
    if not _wait_for_bookmd_activity_focus(adb, "SettingsActivity"):
        print("FAILED: reader Settings button did not open SettingsActivity")
        return False
    settings_xml = _wait_for_ui(adb, lambda current: _node_by_text_casefold(current, "Theme") is not None)
    theme_button = _node_by_text_casefold(settings_xml, "Theme")
    if theme_button is None or not _tap_node(adb, theme_button):
        print("FAILED: Android settings screen did not expose Theme")
        return False
    if _adb([str(adb), "shell", "input", "keyevent", "4"]).returncode != 0:
        print("FAILED: unable to return from Android settings screen")
        return False
    if not _wait_for_bookmd_activity_focus(adb, "ReaderActivity"):
        print("FAILED: Android settings did not return to reader")
        return False
    reader_xml_after_settings = _wait_for_ui(adb, lambda current: "android.webkit.WebView" in current)
    if "android.webkit.WebView" not in reader_xml_after_settings:
        print("FAILED: reader did not render after settings round trip")
        return False
    return True


def _progress_saved(adb: Path, book_dir: str) -> bool:
    result = _adb(
        [
            str(adb),
            "shell",
            _run_as_shell_command("cat shared_prefs/bookmd_progress.xml 2>/dev/null || true"),
        ]
    )
    if result.returncode != 0:
        return False
    return f'{book_dir}:chapter_path' in result.stdout and f'{book_dir}:updated_at' in result.stdout


def _restore_progress_from_shelf(adb: Path, title: str) -> str:
    for command in (
        [str(adb), "shell", "am", "force-stop", PACKAGE_NAME],
        [str(adb), "shell", "am", "start", "-S", "-n", f"{PACKAGE_NAME}/.BookShelfActivity"],
    ):
        if _adb(command).returncode != 0:
            return ""
    if not _assert_app_running(adb):
        return ""
    if not _assert_bookmd_focus(adb):
        return ""
    shelf_xml = _wait_for_ui(
        adb,
        lambda current: (not title or _node_by_text(current, title) is not None) and "Last read:" in current,
    )
    node = _node_by_text(shelf_xml, title) if title else None
    if node is None:
        node = _first_clickable_text_node(shelf_xml, excluded_texts={"IMPORT .BOOKMD", "LOGS", "DELETE"})
    if node is None or not _tap_node(adb, node):
        return ""
    if not _wait_for_bookmd_activity_focus(adb, "ReaderActivity"):
        return ""
    return _wait_for_ui(adb, lambda current: "android.webkit.WebView" in current)


def _search_result_node(xml: str) -> dict[str, str] | None:
    for node in _iter_ui_nodes(xml):
        text = node.get("text", "").strip()
        bounds = node.get("bounds", "")
        class_name = node.get("class", "")
        if node.get("clickable") != "true" or not text or not bounds:
            continue
        if text.casefold() == "search" or class_name == "android.widget.EditText":
            continue
        return node
    return None


def _tap_source_block(adb: Path, reader_xml: str) -> bool:
    block = _source_block_node(reader_xml)
    if block is not None:
        return _tap_node(adb, block)
    webview = _node_by_class(reader_xml, "android.webkit.WebView")
    if webview is None:
        return False
    left, top, right, bottom = _bounds_tuple(webview["bounds"])
    x = (left + right) // 2
    y = min(bottom - 20, top + 240)
    return _adb([str(adb), "shell", "input", "tap", str(x), str(y)]).returncode == 0


def _source_block_node(reader_xml: str) -> dict[str, str] | None:
    excluded = {"toc", "prev", "next", "search", "settings"}
    candidates = []
    for node in _iter_ui_nodes(reader_xml):
        text = node.get("text", "").strip()
        bounds = node.get("bounds", "")
        if node.get("clickable") != "true" or not text or not bounds:
            continue
        if text.casefold() in excluded:
            continue
        left, top, right, bottom = _bounds_tuple(bounds)
        area = max(0, right - left) * max(0, bottom - top)
        if area <= 0:
            continue
        candidates.append((area, node))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _bounds_tuple(bounds: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if not match:
        raise ValueError(f"invalid Android UI bounds: {bounds}")
    return tuple(int(value) for value in match.groups())


def _adb_input_text(text: str) -> str:
    return text.replace("%", "%25").replace(" ", "%s")


if __name__ == "__main__":
    raise SystemExit(main())
