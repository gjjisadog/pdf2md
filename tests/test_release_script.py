from pathlib import Path
import json
import importlib.util
import subprocess
import zipfile


def test_release_verification_script_documents_required_checks():
    script = Path("scripts/verify_release.py").read_text(encoding="utf-8")

    assert "python -m pytest" in script
    assert "converter" in script
    assert "validate" in script
    assert "test_ocr_client.py" in script
    assert "assembleDebug" in script
    assert "ANDROID_HOME" in script
    assert "apps/reader-ios/scripts/verify_ios_release.py" in script
    assert "--allow-xcode-blocked" not in script


def test_ios_release_gate_runs_core_compile_verification():
    script = Path("apps/reader-ios/scripts/verify_ios_release.py").read_text(encoding="utf-8")

    assert "scripts/verify_ios_core.py" in script
    assert "--compile-only" in script


def test_ios_release_gate_allows_slow_static_verification():
    script = Path("apps/reader-ios/scripts/verify_ios_release.py").read_text(encoding="utf-8")

    assert 'run(["python3", "scripts/verify_ios_static.py"], timeout=180)' in script


def test_android_reader_verification_script_runs_required_checks():
    script = Path("scripts/verify_android_reader.py").read_text(encoding="utf-8")

    assert "sync_android_renderer_assets.py" in script
    assert "tests/test_android_skeleton.py" in script
    assert "tests/test_renderer_assets.py" in script
    assert "assembleDebug" in script
    assert "ANDROID_HOME" in script
    assert "ANDROID_SDK_ROOT" in script
    assert "--artifacts-dir" in script
    assert "_collect_device_artifacts" in script
    assert "_preflight_aapt2" in script


def _load_android_verify_script():
    path = Path("scripts/verify_android_reader.py")
    spec = importlib.util.spec_from_file_location("verify_android_reader", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_ios_release_script():
    path = Path("apps/reader-ios/scripts/verify_ios_release.py")
    spec = importlib.util.spec_from_file_location("verify_ios_release", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_ios_core_script():
    path = Path("apps/reader-ios/scripts/verify_ios_core.py")
    spec = importlib.util.spec_from_file_location("verify_ios_core", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_ios_static_script():
    path = Path("apps/reader-ios/scripts/verify_ios_static.py")
    spec = importlib.util.spec_from_file_location("verify_ios_static", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ios_static_sample_rejects_duplicate_chapter_orders(tmp_path, monkeypatch):
    module = _load_ios_static_script()
    sample = tmp_path / "duplicate_order.bookmd"
    chapters = [
        {
            "id": f"chapter-{index:03d}",
            "title": f"Chapter {index}",
            "path": f"chapters/{index:03d}.md",
            "order": 1 if index == 2 else index,
        }
        for index in range(1, 19)
    ]
    with zipfile.ZipFile(sample, "w") as archive:
        archive.writestr("book.json", json.dumps({"title": "Book", "chapters": chapters}))
        archive.writestr("reading_config.json", "{}")
        archive.writestr("translation.json", "{}")
        archive.writestr("terms.json", json.dumps({"terms": [{"source": "A", "target": "B"}]}))
        archive.writestr(
            "search_index.json",
            json.dumps(
                {
                    "items": [
                        {
                            "block_id": "p001_b001",
                            "chapter_id": "chapter-001",
                            "chapter_path": "chapters/001.md",
                            "chapter_title": "Chapter 1",
                            "type": "paragraph",
                            "text": "Converter",
                        }
                    ]
                }
            ),
        )
        archive.writestr(
            "source_map.json",
            json.dumps(
                {
                    "blocks": [
                        {
                            "block_id": "p001_b001",
                            "chapter_id": "chapter-001",
                            "markdown_path": "chapters/001.md",
                            "source_page": 1,
                            "bbox": [1, 2, 3, 4],
                            "source_text": "Converter",
                            "translated_text": None,
                            "type": "paragraph",
                        }
                    ]
                }
            ),
        )
        archive.writestr("source/original.pdf", b"%PDF-1.4\n")
        for chapter in chapters:
            text = "trace: p001_b001\nConverter\n" if chapter["path"] == "chapters/001.md" else "body\n"
            archive.writestr(chapter["path"], text)

    monkeypatch.setattr(module, "SAMPLE", sample)

    try:
        module.verify_sample()
    except AssertionError as error:
        assert "duplicate chapter order" in str(error)
    else:
        raise AssertionError("verify_sample should reject duplicate chapter orders")


def test_ios_zip_archive_rejects_duplicate_paths_without_dictionary_trap():
    archive_source = Path("apps/reader-ios/Sources/BookMDReaderCore/BookMDArchive.swift").read_text(
        encoding="utf-8"
    )

    assert "case duplicateArchivePath(String)" in archive_source
    assert "BookMD 包含重复路径" in archive_source
    assert "Dictionary(uniqueKeysWithValues:" not in archive_source
    assert "if entriesByPath[entry.path] != nil" in archive_source


def test_ios_progress_store_recovers_from_corrupt_progress_json():
    store_source = Path("apps/reader-ios/Sources/BookMDReaderCore/ReadingProgressStore.swift").read_text(
        encoding="utf-8"
    )

    assert "recoverCorruptStorage" in store_source
    assert ".corrupt-" in store_source
    assert "try? FileManager.default.moveItem(at: storageURL, to: backupURL)" in store_source
    assert "self.storage = Storage()" in store_source


def test_ios_core_compile_only_skips_running_generated_binary(tmp_path, monkeypatch):
    module = _load_ios_core_script()
    sample = tmp_path / "sample.bookmd"
    sample.write_bytes(b"placeholder")
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "SAMPLE", sample)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.main(["--compile-only"]) == 0
    assert any(command[0] == "cc" for command in calls)
    assert any(command[0] == "swiftc" for command in calls)
    assert not any(len(command) == 1 and str(command[0]).endswith("verify-ios-core") for command in calls)


def test_ios_core_runtime_timeout_reports_readable_error(tmp_path, monkeypatch):
    module = _load_ios_core_script()
    sample = tmp_path / "sample.bookmd"
    sample.write_bytes(b"placeholder")
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if len(command) == 1 and str(command[0]).endswith("verify-ios-core"):
            raise subprocess.TimeoutExpired(command, timeout=30)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "SAMPLE", sample)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    try:
        module.main([])
    except SystemExit as error:
        assert "iOS core runtime verifier timed out" in str(error)
        assert "Use --compile-only" in str(error)
    else:
        raise AssertionError("verify_ios_core should report a readable runtime timeout")
    assert any(len(command) == 1 and str(command[0]).endswith("verify-ios-core") for command in calls)


def test_ios_core_compile_uses_temporary_source_snapshots():
    script = Path("apps/reader-ios/scripts/verify_ios_core.py").read_text(encoding="utf-8")

    assert "import shutil" in script
    assert "snapshot_swift_sources" in script
    assert "shutil.copy2" in script
    assert "source_snapshot" in script


def test_ios_release_destination_reports_simctl_timeout(monkeypatch):
    module = _load_ios_release_script()

    def fake_run(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, timeout=30)

    monkeypatch.setattr(module, "run", fake_run)

    try:
        module.resolve_destination("auto")
    except RuntimeError as error:
        assert "xcrun simctl timed out" in str(error)
        assert "Repair the local Xcode simulator installation" in str(error)
    else:
        raise AssertionError("resolve_destination should fail with a readable simctl timeout")


def test_android_reader_device_smoke_helpers_parse_ui_bounds_and_clickable_nodes():
    module = _load_android_verify_script()
    xml = """<?xml version='1.0' encoding='UTF-8'?>
    <hierarchy>
      <node text="IMPORT .BOOKMD" class="android.widget.Button" clickable="true" bounds="[32,95][1048,221]" />
      <node text="三相电压源逆变器的新型广义不连续SVPWM 策略研究" class="android.widget.TextView" clickable="true" bounds="[32,375][1048,525]" />
      <node text="Last read: never" class="android.widget.TextView" clickable="false" bounds="[32,525][1048,574]" />
    </hierarchy>
    """

    node = module._first_clickable_text_node(
        xml,
        excluded_texts={"IMPORT .BOOKMD", "LOGS", "DELETE"},
    )

    assert node is not None
    assert node["text"].startswith("三相电压源")
    assert module._center_of_bounds(node["bounds"]) == (540, 450)


def test_android_reader_aapt2_preflight_reports_timeout(tmp_path, monkeypatch, capsys):
    module = _load_android_verify_script()
    android_home = tmp_path / "android-sdk"
    aapt2 = android_home / "build-tools" / "33.0.2" / "aapt2"
    aapt2.parent.mkdir(parents=True)
    aapt2.write_text("#!/bin/sh\n", encoding="utf-8")
    aapt2.chmod(0o755)

    def fake_run(command, **kwargs):
        assert command == [str(aapt2), "version"]
        assert kwargs["timeout"] == 1
        raise subprocess.TimeoutExpired(command, timeout=1)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._preflight_aapt2(android_home, timeout_seconds=1) is False
    output = capsys.readouterr().out
    assert "FAILED: Android aapt2 cannot start" in output
    assert "timed out after 1s" in output
    assert "Gradle's Maven-provided aapt2 may fail the same way" in output
    assert "macOS process loader/dyld" in output


def test_android_reader_gradle_command_uses_explicit_shell():
    module = _load_android_verify_script()

    command = module._gradle_assemble_command()

    assert command[0] == "sh"
    assert str(command[1]).endswith("apps/reader-android/gradlew")
    assert command[2:] == [":app:assembleDebug"]


def test_android_reader_device_smoke_prefers_largest_visible_source_block():
    module = _load_android_verify_script()
    xml = """<hierarchy>
      <node text="TOC" class="android.widget.Button" clickable="true" bounds="[0,63][360,189]" />
      <node text="IEEE TRANSACTIONS" class="android.widget.TextView" clickable="true" bounds="[21,420][1002,588]" />
      <node text="三相电压源逆变器的新型广义不连续SVPWM 策略研究" class="android.widget.TextView" clickable="true" bounds="[21,777][1002,1275]" />
      <node text="Hidden" class="android.widget.TextView" clickable="true" bounds="[0,0][0,0]" />
    </hierarchy>"""

    node = module._source_block_node(xml)

    assert node is not None
    assert node["text"].startswith("三相电压源")


def test_android_reader_device_smoke_ignores_reader_toolbar_when_picking_chapter():
    module = _load_android_verify_script()
    xml = """<hierarchy>
      <node text="TOC" class="android.widget.Button" clickable="true" bounds="[0,63][360,189]" />
      <node text="Prev" class="android.widget.Button" clickable="true" bounds="[360,63][720,189]" />
      <node text="Next" class="android.widget.Button" clickable="true" bounds="[720,63][1080,189]" />
      <node text="Search" class="android.widget.Button" clickable="true" bounds="[0,189][540,315]" />
      <node text="Settings" class="android.widget.Button" clickable="true" bounds="[540,189][1080,315]" />
      <node text="Chapter 1" class="android.widget.TextView" clickable="true" bounds="[32,511][1048,693]" />
    </hierarchy>"""

    node = module._chapter_node(xml)

    assert node is not None
    assert node["text"] == "Chapter 1"


def test_android_reader_device_smoke_scrolls_shelf_to_find_target_book(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    calls = []
    xml = iter(
        [
            "<hierarchy><node text=\"Untitled\" clickable=\"true\" bounds=\"[32,375][1048,525]\" /></hierarchy>",
            "<hierarchy><node text=\"Target Book\" clickable=\"true\" bounds=\"[32,805][1048,937]\" /></hierarchy>",
        ]
    )

    def fake_dump(_adb):
        return next(xml)

    def fake_adb(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_dump_ui_xml", fake_dump)
    monkeypatch.setattr(module, "_adb", fake_adb)

    node = module._find_book_node_on_shelf(adb, "Target Book")

    assert node is not None
    assert node["text"] == "Target Book"
    assert [str(adb), "shell", "input", "swipe", "540", "1650", "540", "500"] in calls


def test_android_reader_device_smoke_ignores_search_input_when_picking_result():
    module = _load_android_verify_script()
    xml = """<hierarchy>
      <node text="SVPWM" class="android.widget.EditText" clickable="true" bounds="[32,95][1048,212]" />
      <node text="SEARCH" class="android.widget.Button" clickable="true" bounds="[32,212][1048,338]" />
      <node text="SVPWM result" class="android.widget.TextView" clickable="true" bounds="[32,338][1048,608]" />
    </hierarchy>"""

    node = module._search_result_node(xml)

    assert node is not None
    assert node["text"] == "SVPWM result"


def test_android_reader_device_smoke_retries_misordered_search_input(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    calls = []
    ui_xml = iter(
        [
            '<hierarchy><node text="" class="android.widget.EditText" clickable="true" bounds="[32,95][1048,212]" /></hierarchy>',
            '<hierarchy><node text="vlotage" class="android.widget.EditText" clickable="true" bounds="[32,95][1048,212]" /></hierarchy>',
            '<hierarchy><node text="voltage" class="android.widget.EditText" clickable="true" bounds="[32,95][1048,212]" /></hierarchy>',
        ]
    )

    def fake_adb(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module, "_wait_for_ui", lambda *_args, **_kwargs: next(ui_xml))

    assert module._enter_search_term(adb, "voltage")
    assert calls.count([str(adb), "shell", "input", "text", "voltage"]) == 2
    assert [str(adb), "shell", "input", "keyevent", "67"] in calls


def test_android_reader_device_smoke_exposes_performance_baseline_output():
    script = Path("scripts/verify_android_reader.py").read_text(encoding="utf-8")

    assert "--performance-baseline" in script
    assert "_write_performance_baseline" in script
    assert "performance_baseline.json" in script
    assert "open_to_reader_ms" in script
    assert "search_flow_ms" in script
    assert "source_trace_ms" in script
    assert "total_smoke_ms" in script


def test_android_reader_performance_baseline_writer_outputs_json(tmp_path):
    module = _load_android_verify_script()

    module._write_performance_baseline(
        tmp_path,
        {
            "open_to_reader_ms": 123.4,
            "search_flow_ms": 56.7,
            "source_trace_ms": 89.0,
            "total_smoke_ms": 456.7,
        },
    )

    payload = json.loads((tmp_path / "performance_baseline.json").read_text(encoding="utf-8"))

    assert payload["schema"] == "android_reader_performance_baseline_v1"
    assert payload["metrics"]["open_to_reader_ms"] == 123.4
    assert payload["metrics"]["search_flow_ms"] == 56.7
    assert payload["metrics"]["source_trace_ms"] == 89.0
    assert payload["metrics"]["total_smoke_ms"] == 456.7


def test_android_reader_device_smoke_finds_real_visual_asset_reference(tmp_path):
    module = _load_android_verify_script()
    bookmd = tmp_path / "visual.bookmd"
    with zipfile.ZipFile(bookmd, "w") as archive:
        archive.writestr("book.json", json.dumps({"title": "Visual Book"}))
        archive.writestr("chapters/001.md", "![Cover](../assets/cover/page_001.png)\n\n:::formula id=\"eq\" src=\"../assets/generated/page_001_eq.png\" page=\"1\"\nE=mc^2\n:::\n")
        archive.writestr("assets/cover/page_001.png", b"cover")
        archive.writestr("assets/generated/page_001_eq.png", b"asset")

    assert module._first_visual_asset_reference(bookmd) == "assets/generated/page_001_eq.png"


def test_android_reader_device_smoke_can_open_real_visual_asset(monkeypatch, tmp_path):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    bookmd = tmp_path / "visual.bookmd"
    with zipfile.ZipFile(bookmd, "w") as archive:
        archive.writestr("book.json", json.dumps({"title": "Visual Book"}))
        archive.writestr("chapters/001.md", ":::figure id=\"fig\" src=\"../assets/generated/page_001_fig.png\" page=\"1\"\nFigure\n:::\n")
        archive.writestr("assets/generated/page_001_fig.png", b"asset")
    commands = []

    def fake_adb(command):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module, "_bookmd_activity_has_focus", lambda _adb, activity: activity in {"ImageViewerActivity", "ReaderActivity"})
    monkeypatch.setattr(module, "_wait_for_ui", lambda *_args, **_kwargs: "<hierarchy><node class=\"android.webkit.WebView\" bounds=\"[0,0][1080,1920]\" /></hierarchy>")

    assert module._verify_visual_asset_flow(adb, bookmd, "visual")

    expected_book_dir = f"/data/data/{module.PACKAGE_NAME}/files/visual"
    expected_media_uri = f"file://{expected_book_dir}/assets/generated/page_001_fig.png"
    assert [
        str(adb),
        "shell",
        "am",
        "start",
        "-n",
        f"{module.PACKAGE_NAME}/.BookShelfActivity",
        "--activity-clear-top",
        "--activity-single-top",
        "--ez",
        "smoke_visual_asset",
        "true",
        "--es",
        "book_dir",
        expected_book_dir,
        "--es",
        "media_uri",
        expected_media_uri,
    ] in commands
    assert [str(adb), "shell", "input", "keyevent", "4"] in commands


def test_android_reader_device_smoke_does_not_treat_query_input_as_search_result():
    module = _load_android_verify_script()
    input_only_xml = """<hierarchy>
      <node text="voltage" class="android.widget.EditText" clickable="true" bounds="[32,95][1048,212]" />
      <node text="SEARCH" class="android.widget.Button" clickable="true" bounds="[32,212][1048,338]" />
    </hierarchy>"""
    result_xml = """<hierarchy>
      <node text="voltage" class="android.widget.EditText" clickable="true" bounds="[32,95][1048,212]" />
      <node text="BASIC CONCEPTS&#10;linear voltage regulators" class="android.widget.TextView" clickable="true" bounds="[32,338][1048,608]" />
    </hierarchy>"""
    no_results_xml = """<hierarchy>
      <node text="voltage" class="android.widget.EditText" clickable="true" bounds="[32,95][1048,212]" />
      <node text="No results." class="android.widget.TextView" bounds="[32,338][1048,434]" />
    </hierarchy>"""

    assert not module._search_results_ready(input_only_xml, "voltage")
    assert module._search_results_ready(result_xml, "voltage")
    assert module._search_results_ready(no_results_xml, "voltage")


def test_android_reader_verification_script_can_run_optional_device_smoke(
    tmp_path,
    monkeypatch,
):
    module = _load_android_verify_script()
    android_home = tmp_path / "sdk"
    adb = android_home / "platform-tools" / "adb"
    adb.parent.mkdir(parents=True)
    adb.write_text("fake adb", encoding="utf-8")
    apk = module.ANDROID_PROJECT / "app/build/outputs/apk/debug/app-debug.apk"
    bookmd = tmp_path / "formula sample.bookmd"
    with zipfile.ZipFile(bookmd, "w") as archive:
        archive.writestr("book.json", json.dumps({"title": "Book"}))
    commands = []

    def fake_android_home():
        return android_home

    def fake_run(command, cwd, env=None):
        commands.append(command)
        return 0

    ui_xml = iter(
        [
            "<hierarchy><node text=\"Untitled\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,375][1048,525]\" /><node text=\"Book\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,805][1048,937]\" /></hierarchy>",
            "<hierarchy></hierarchy>",
            "<hierarchy><node text=\"SEARCH\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,171][1048,297]\" /><node text=\"SETTINGS\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,297][1048,423]\" /><node text=\"Chapter 1\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,511][1048,693]\" /></hierarchy>",
            "<hierarchy><node text=\"Search\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[0,189][540,315]\" /><node class=\"android.webkit.WebView\" bounds=\"[0,315][1080,1857]\" /></hierarchy>",
            "<hierarchy><node text=\"\" class=\"android.widget.EditText\" clickable=\"true\" bounds=\"[32,95][1048,212]\" /><node text=\"SEARCH\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,212][1048,338]\" /></hierarchy>",
            "<hierarchy><node text=\"SVPWM\" class=\"android.widget.EditText\" clickable=\"true\" bounds=\"[32,95][1048,212]\" /><node text=\"SEARCH\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,212][1048,338]\" /></hierarchy>",
            "<hierarchy><node text=\"SVPWM\" class=\"android.widget.EditText\" clickable=\"true\" bounds=\"[32,95][1048,212]\" /><node text=\"SEARCH\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,212][1048,338]\" /></hierarchy>",
            "<hierarchy><node text=\"SVPWM result\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,338][1048,608]\" /></hierarchy>",
            "<hierarchy><node text=\"Search\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[0,189][540,315]\" /><node text=\"SVPWM heading\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[49,433][1031,931]\" /><node class=\"android.webkit.WebView\" bounds=\"[0,315][1080,1857]\" /></hierarchy>",
            "<hierarchy><node text=\"Source: p001_b003\" class=\"android.widget.TextView\" bounds=\"[133,676][947,746]\" /><node text=\"OPEN PDF PAGE\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[102,1153][450,1279]\" /></hierarchy>",
            "<hierarchy><node class=\"android.view.View\" content-desc=\"Page 1 [31,59,1135,178]\" bounds=\"[0,63][1080,1641]\" /></hierarchy>",
        ]
    )

    def fake_subprocess_run(command, cwd=None, text=False, env=None, check=False, capture_output=False, timeout=None):
        commands.append(command)
        if "cat" in command and "/sdcard/window.xml" in command:
            stdout = next(ui_xml)
        elif command[-1:] == ["devices"]:
            stdout = "List of devices attached\nemulator-5554\tdevice\n"
        elif "pidof" in command:
            stdout = "1234\n"
        elif "dumpsys" in command and "activity" in command:
            stdout = (
                "mCurrentFocus=Window{abc u0 com.bookmd.reader/com.bookmd.reader.TocActivity}\n"
                "mFocusedApp=ActivityRecord{def u0 com.bookmd.reader/.ReaderActivity}\n"
            )
        else:
            stdout = ""
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(module, "_android_home", fake_android_home)
    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)

    exit_code = module.main(
        [
            "--device-smoke",
            "--bookmd",
            str(bookmd),
            "--search-term",
            "SVPWM",
        ]
    )

    assert exit_code == 0
    assert [str(adb), "install", "-r", str(apk)] in commands
    assert [str(adb), "shell", "pm", "clear", module.PACKAGE_NAME] in commands
    assert commands.index([str(adb), "shell", "pm", "clear", module.PACKAGE_NAME]) < commands.index(
        [str(adb), "push", str(bookmd), "/data/local/tmp/formula_sample.bookmd"]
    )
    assert [str(adb), "push", str(bookmd), "/data/local/tmp/formula_sample.bookmd"] in commands
    run_as_command = next(command for command in commands if command[:2] == [str(adb), "shell"] and "run-as" in command[2])
    assert run_as_command[2].startswith("run-as com.bookmd.reader /system/bin/sh -c ")
    assert "mkdir -p files && rm -rf files/formula_sample" in run_as_command[2]
    assert "formula_sample.bookmd" in run_as_command[2]
    assert [str(adb), "shell", "am", "force-stop", "com.google.android.documentsui"] in commands
    assert [str(adb), "shell", "am", "start", "-S", "-n", "com.bookmd.reader/.BookShelfActivity"] in commands
    assert [str(adb), "shell", "input", "text", "SVPWM"] in commands
    taps = [command for command in commands if command[:4] == [str(adb), "shell", "input", "tap"]]
    assert len(taps) >= 5
    assert [str(adb), "shell", "input", "tap", "540", "871"] in commands
    assert [str(adb), "shell", "input", "tap", "276", "1216"] in commands


def test_android_reader_device_smoke_can_import_through_file_picker(
    tmp_path,
    monkeypatch,
):
    module = _load_android_verify_script()
    android_home = tmp_path / "sdk"
    adb = android_home / "platform-tools" / "adb"
    adb.parent.mkdir(parents=True)
    adb.write_text("fake adb", encoding="utf-8")
    bookmd = tmp_path / "real import.bookmd"
    with zipfile.ZipFile(bookmd, "w") as archive:
        archive.writestr("book.json", json.dumps({"title": "Imported Book"}))
    commands = []

    def fake_android_home():
        return android_home

    def fake_run(command, cwd, env=None):
        commands.append(command)
        return 0

    ui_xml = iter(
        [
            "<hierarchy><node text=\"IMPORT .BOOKMD\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,95][1048,221]\" /></hierarchy>",
            "<hierarchy><node text=\"IMPORT .BOOKMD\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,95][1048,221]\" /></hierarchy>",
            "<hierarchy><node text=\"real_import.bookmd\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,375][1048,525]\" /></hierarchy>",
            "<hierarchy><node text=\"Imported: real_import\" class=\"android.widget.TextView\" bounds=\"[32,375][1048,525]\" /></hierarchy>",
            "<hierarchy><node text=\"Imported Book\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,375][1048,525]\" /></hierarchy>",
            "<hierarchy></hierarchy>",
            "<hierarchy><node text=\"SEARCH\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,171][1048,297]\" /><node text=\"SETTINGS\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,297][1048,423]\" /><node text=\"Chapter 1\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,511][1048,693]\" /></hierarchy>",
            "<hierarchy><node class=\"android.webkit.WebView\" bounds=\"[0,315][1080,1857]\" /></hierarchy>",
            "<hierarchy><node text=\"Source: p001_b003\" class=\"android.widget.TextView\" bounds=\"[133,676][947,746]\" /><node text=\"OPEN PDF PAGE\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[102,1153][450,1279]\" /></hierarchy>",
            "<hierarchy><node class=\"android.view.View\" content-desc=\"Page 1 [31,59,1135,178]\" bounds=\"[0,63][1080,1641]\" /></hierarchy>",
        ]
    )

    def fake_subprocess_run(command, cwd=None, text=False, env=None, check=False, capture_output=False, timeout=None):
        commands.append(command)
        if "cat" in command and "/sdcard/window.xml" in command:
            stdout = next(ui_xml)
        elif command[-1:] == ["devices"]:
            stdout = "List of devices attached\nemulator-5554\tdevice\n"
        elif "pidof" in command:
            stdout = "1234\n"
        elif "dumpsys" in command and "activity" in command:
            if any("real_import.bookmd" in item for item in command):
                stdout = ""
            else:
                stdout = (
                    "mCurrentFocus=Window{abc u0 com.bookmd.reader/com.bookmd.reader.BookImportActivity}\n"
                    "mFocusedApp=ActivityRecord{def u0 com.bookmd.reader/.TocActivity}\n"
                    "mFocusedApp=ActivityRecord{ghi u0 com.bookmd.reader/.ReaderActivity}\n"
                )
        else:
            stdout = ""
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(module, "_android_home", fake_android_home)
    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(module, "_wait_for_bookmd_activity_focus", lambda _adb, _activity_name: True)

    exit_code = module.main(
        [
            "--device-smoke",
            "--bookmd",
            str(bookmd),
            "--import-via-picker",
        ]
    )

    assert exit_code == 0
    assert [str(adb), "push", str(bookmd), "/sdcard/Download/real_import.bookmd"] in commands
    assert [str(adb), "shell", "am", "force-stop", "com.google.android.documentsui"] in commands
    assert [str(adb), "shell", "input", "tap", "540", "158"] in commands
    assert commands.count([str(adb), "shell", "input", "tap", "540", "158"]) == 2
    assert [str(adb), "shell", "input", "tap", "540", "450"] in commands
    assert [str(adb), "shell", "input", "keyevent", "4"] in commands
    assert not any(command[:3] == [str(adb), "shell", "run-as"] for command in commands)


def test_android_reader_file_picker_waits_for_import_activity_before_second_button(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    focused_activities = []
    ui_xml = iter(
        [
            "<hierarchy><node text=\"IMPORT .BOOKMD\" clickable=\"true\" bounds=\"[32,95][1048,221]\" /></hierarchy>",
            "<hierarchy><node text=\"IMPORT .BOOKMD\" clickable=\"true\" bounds=\"[32,95][1048,221]\" /></hierarchy>",
            "<hierarchy><node text=\"Imported: sample\" bounds=\"[32,375][1048,525]\" /></hierarchy>",
        ]
    )

    monkeypatch.setattr(module, "_wait_for_ui", lambda *_args, **_kwargs: next(ui_xml))
    monkeypatch.setattr(module, "_tap_node", lambda _adb, _node: True)
    monkeypatch.setattr(module, "_find_document_node_in_picker", lambda _adb, _name: {"text": _name, "bounds": "[32,375][1048,525]"})
    monkeypatch.setattr(module, "_adb", lambda command: subprocess.CompletedProcess(command, 0, "", ""))
    monkeypatch.setattr(module, "_assert_bookmd_focus", lambda _adb: True)

    def fake_activity_focus(_adb, activity_name):
        focused_activities.append(activity_name)
        return True

    monkeypatch.setattr(module, "_bookmd_activity_has_focus", fake_activity_focus)

    assert module._import_book_via_picker(adb, "sample.bookmd", "")
    assert "BookImportActivity" in focused_activities


def test_android_reader_file_picker_does_not_press_back_when_import_returns_to_shelf(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    calls = []
    ui_xml = iter(
        [
            "<hierarchy><node text=\"IMPORT .BOOKMD\" clickable=\"true\" bounds=\"[32,95][1048,221]\" /></hierarchy>",
            "<hierarchy><node text=\"IMPORT .BOOKMD\" clickable=\"true\" bounds=\"[32,95][1048,221]\" /></hierarchy>",
            "<hierarchy><node text=\"Imported Book\" clickable=\"true\" bounds=\"[32,375][1048,525]\" /></hierarchy>",
        ]
    )

    monkeypatch.setattr(module, "_wait_for_ui", lambda *_args, **_kwargs: next(ui_xml))
    monkeypatch.setattr(module, "_tap_node", lambda _adb, _node: True)
    monkeypatch.setattr(module, "_find_document_node_in_picker", lambda _adb, _name: {"text": _name, "bounds": "[32,375][1048,525]"})

    def fake_adb(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module, "_assert_bookmd_focus", lambda _adb: True)
    monkeypatch.setattr(module, "_wait_for_bookmd_activity_focus", lambda _adb, _activity_name: True)
    monkeypatch.setattr(module, "_bookmd_activity_has_focus", lambda _adb, activity_name: activity_name != "BookImportActivity")

    assert module._import_book_via_picker(adb, "sample.bookmd", "Imported Book")
    assert [str(adb), "shell", "input", "keyevent", "4"] not in calls


def test_android_reader_device_smoke_opens_downloads_when_recent_misses_file(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    calls = []
    xml = iter(
        [
            "<hierarchy><node text=\"Old file\" clickable=\"true\" bounds=\"[32,375][1048,525]\" /></hierarchy>",
            "<hierarchy><node content-desc=\"Show roots\" clickable=\"true\" bounds=\"[0,63][147,189]\" /></hierarchy>",
            "<hierarchy><node text=\"Downloads\" clickable=\"false\" bounds=\"[168,699][714,750]\" /></hierarchy>",
            "<hierarchy><node text=\"target.bookmd\" clickable=\"true\" bounds=\"[189,168][744,225]\" /></hierarchy>",
        ]
    )

    def fake_dump(_adb):
        return next(xml)

    def fake_adb(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_dump_ui_xml", fake_dump)
    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    node = module._find_document_node_in_picker(adb, "target.bookmd", attempts=1)

    assert node is not None
    assert node["text"] == "target.bookmd"
    assert [str(adb), "shell", "input", "tap", "73", "126"] in calls
    assert [str(adb), "shell", "input", "tap", "441", "724"] in calls


def test_android_reader_device_smoke_selects_documentsui_card_when_title_is_not_clickable():
    module = _load_android_verify_script()
    xml = """<hierarchy>
      <node text="" resource-id="com.google.android.documentsui:id/item_root" class="androidx.cardview.widget.CardView" clickable="true" bounds="[64,613][529,1214]">
        <node text="" class="android.widget.RelativeLayout" clickable="false" bounds="[64,613][529,1214]">
          <node text="formula_svpwm.bookmd" resource-id="android:id/title" class="android.widget.TextView" clickable="false" bounds="[196,1099][497,1150]" />
        </node>
      </node>
    </hierarchy>"""

    node = module._document_node(xml, "formula_svpwm.bookmd")

    assert node is not None
    assert node["resource-id"] == "com.google.android.documentsui:id/item_root"
    assert module._center_of_bounds(node["bounds"]) == (296, 913)


def test_android_reader_device_smoke_can_verify_settings_round_trip(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    calls = []
    reader_xml = """<hierarchy>
      <node text="Settings" class="android.widget.Button" clickable="true" bounds="[540,189][1080,315]" />
      <node class="android.webkit.WebView" bounds="[0,315][1080,1857]" />
    </hierarchy>"""
    ui_xml = iter(
        [
            "<hierarchy><node text=\"Theme\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,633][1048,759]\" /></hierarchy>",
            reader_xml,
        ]
    )

    def fake_adb(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module, "_wait_for_bookmd_activity_focus", lambda _adb, _activity_name: True)
    monkeypatch.setattr(module, "_wait_for_ui", lambda *_args, **_kwargs: next(ui_xml))

    assert module._verify_settings_flow(adb, reader_xml)
    assert [str(adb), "shell", "input", "tap", "810", "252"] in calls
    assert [str(adb), "shell", "input", "tap", "540", "696"] in calls
    assert [str(adb), "shell", "input", "keyevent", "4"] in calls


def test_android_reader_device_smoke_accepts_uppercase_settings_buttons(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    calls = []
    reader_xml = """<hierarchy>
      <node text="SETTINGS" class="android.widget.Button" clickable="true" bounds="[540,189][1080,315]" />
      <node class="android.webkit.WebView" bounds="[0,315][1080,1857]" />
    </hierarchy>"""
    ui_xml = iter(
        [
            "<hierarchy><node text=\"THEME\" class=\"android.widget.Button\" clickable=\"true\" bounds=\"[32,633][1048,759]\" /></hierarchy>",
            reader_xml,
        ]
    )

    def fake_adb(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module, "_wait_for_bookmd_activity_focus", lambda _adb, _activity_name: True)
    monkeypatch.setattr(module, "_wait_for_ui", lambda *_args, **_kwargs: next(ui_xml))

    assert module._verify_settings_flow(adb, reader_xml)
    assert [str(adb), "shell", "input", "tap", "810", "252"] in calls
    assert [str(adb), "shell", "input", "tap", "540", "696"] in calls


def test_android_reader_device_smoke_detects_saved_progress(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")

    def fake_adb(command):
        return subprocess.CompletedProcess(
            command,
            0,
            '<map><string name="formula:chapter_path">chapters/001.md</string><long name="formula:updated_at" value="1" /></map>',
            "",
        )

    monkeypatch.setattr(module, "_adb", fake_adb)

    assert module._progress_saved(adb, "formula")


def test_android_reader_device_smoke_restores_saved_progress_from_shelf(monkeypatch):
    module = _load_android_verify_script()
    adb = Path("/sdk/platform-tools/adb")
    calls = []
    ui_xml = iter(
        [
            "<hierarchy><node text=\"Book\" class=\"android.widget.TextView\" clickable=\"true\" bounds=\"[32,375][1048,525]\" /><node text=\"Last read: 001_chapter.md · Page 2/10\" /></hierarchy>",
            "<hierarchy><node class=\"android.webkit.WebView\" bounds=\"[0,315][1080,1857]\" /></hierarchy>",
        ]
    )

    def fake_adb(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module, "_assert_app_running", lambda _adb: True)
    monkeypatch.setattr(module, "_assert_bookmd_focus", lambda _adb: True)
    monkeypatch.setattr(module, "_wait_for_bookmd_activity_focus", lambda _adb, activity_name: activity_name == "ReaderActivity")
    monkeypatch.setattr(module, "_wait_for_ui", lambda *_args, **_kwargs: next(ui_xml))

    xml = module._restore_progress_from_shelf(adb, "Book")

    assert "android.webkit.WebView" in xml
    assert [str(adb), "shell", "am", "force-stop", "com.bookmd.reader"] in calls
    assert [str(adb), "shell", "am", "start", "-S", "-n", "com.bookmd.reader/.BookShelfActivity"] in calls
    assert [str(adb), "shell", "input", "tap", "540", "450"] in calls


def test_android_reader_device_smoke_selects_chapter_without_tapping_settings():
    module = _load_android_verify_script()
    xml = """<hierarchy>
      <node text="Book Title" class="android.widget.TextView" clickable="false" bounds="[32,95][1048,171]" />
      <node text="Search" class="android.widget.Button" clickable="true" bounds="[32,171][1048,297]" />
      <node text="Settings" class="android.widget.Button" clickable="true" bounds="[32,297][1048,423]" />
      <node text="1. Introduction" class="android.widget.TextView" clickable="true" bounds="[44,447][1036,561]" />
    </hierarchy>"""

    node = module._chapter_node(xml)

    assert node is not None
    assert node["text"] == "1. Introduction"


def test_android_reader_device_smoke_toc_visible_requires_toolbar_and_chapter():
    module = _load_android_verify_script()
    shelf_xml = """<hierarchy>
      <node text="Untitled" class="android.widget.TextView" clickable="true" bounds="[32,297][1048,423]" />
    </hierarchy>"""
    toc_xml = """<hierarchy>
      <node text="SEARCH" class="android.widget.Button" clickable="true" bounds="[32,171][1048,297]" />
      <node text="SETTINGS" class="android.widget.Button" clickable="true" bounds="[32,297][1048,423]" />
      <node text="Untitled" class="android.widget.TextView" clickable="true" bounds="[32,423][1048,533]" />
    </hierarchy>"""

    assert not module._toc_visible(shelf_xml)
    assert module._toc_visible(toc_xml)


def test_android_reader_device_smoke_waits_for_reader_process(monkeypatch):
    module = _load_android_verify_script()
    calls = []

    def fake_adb(command):
        calls.append(command)
        stdout = "" if len(calls) < 3 else "1234\n"
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    assert module._assert_app_running(Path("/sdk/platform-tools/adb"))
    assert len(calls) == 3


def test_android_reader_device_smoke_waits_for_bookmd_focus(monkeypatch):
    module = _load_android_verify_script()
    calls = []

    def fake_adb(command):
        calls.append(command)
        stdout = (
            "mCurrentFocus=Window{abc u0 com.google.android.documentsui/com.android.documentsui.picker.PickActivity}\n"
            if len(calls) < 2
            else "mCurrentFocus=Window{def u0 com.bookmd.reader/com.bookmd.reader.BookShelfActivity}\n"
        )
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    assert module._assert_bookmd_focus(Path("/sdk/platform-tools/adb"))
    assert len(calls) == 2


def test_android_reader_device_smoke_fails_fast_without_connected_device(monkeypatch):
    module = _load_android_verify_script()

    def fake_adb(command):
        return subprocess.CompletedProcess(
            command,
            0,
            "List of devices attached\n\n",
            "",
        )

    monkeypatch.setattr(module, "_adb", fake_adb)

    assert not module._assert_device_connected(Path("/sdk/platform-tools/adb"))


def test_android_reader_device_smoke_accepts_source_dialog_button_as_open():
    module = _load_android_verify_script()
    xml = (
        '<hierarchy><node text="OPEN PDF PAGE" class="android.widget.Button" '
        'clickable="true" bounds="[102,1153][450,1279]" /></hierarchy>'
    )

    assert module._source_dialog_visible(xml)


def test_android_reader_device_smoke_accepts_source_page_activity_as_open(monkeypatch):
    module = _load_android_verify_script()

    def fake_adb(command):
        assert "dumpsys" in command
        return subprocess.CompletedProcess(
            command,
            0,
            "mCurrentFocus=Window{def u0 com.bookmd.reader/com.bookmd.reader.SourcePageActivity}\n",
            "",
        )

    monkeypatch.setattr(module, "_adb", fake_adb)

    assert module._source_page_visible(Path("/sdk/platform-tools/adb"), "<hierarchy />")


def test_android_reader_device_smoke_collects_failure_artifacts(tmp_path, monkeypatch):
    module = _load_android_verify_script()
    commands = []

    def fake_adb(command):
        commands.append(command)
        if command[-3:] == ["shell", "cat", "/sdcard/window.xml"]:
            return subprocess.CompletedProcess(command, 0, "<hierarchy />", "")
        if command[-4:] == ["shell", "dumpsys", "activity", "activities"]:
            return subprocess.CompletedProcess(command, 0, "focus", "")
        return subprocess.CompletedProcess(command, 0, "log", "")

    monkeypatch.setattr(module, "_adb", fake_adb)
    monkeypatch.setattr(module, "_adb_binary", lambda _command: b"PNG")

    module._collect_device_artifacts(Path("/sdk/platform-tools/adb"), tmp_path)

    assert (tmp_path / "screenshot.png").exists()
    assert (tmp_path / "window.xml").read_text(encoding="utf-8") == "<hierarchy />"
    assert (tmp_path / "window_focus.txt").read_text(encoding="utf-8") == "focus"
    assert (tmp_path / "logcat_tail.txt").read_text(encoding="utf-8") == "log"


def test_android_reader_ui_dump_times_out_instead_of_hanging(monkeypatch):
    module = _load_android_verify_script()

    def fake_run(command, **_kwargs):
        if "uiautomator" in command:
            raise subprocess.TimeoutExpired(command, timeout=3)
        return subprocess.CompletedProcess(command, 0, "<hierarchy />", "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._dump_ui_xml(Path("/sdk/platform-tools/adb")) == ""


def test_android_reader_adb_command_times_out_instead_of_hanging(monkeypatch):
    module = _load_android_verify_script()

    def fake_run(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, timeout=10)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module._adb(["adb", "shell", "true"])

    assert result.returncode == 124
    assert "timed out" in result.stderr
