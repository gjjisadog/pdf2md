from pathlib import Path


def test_android_reader_skeleton_has_webview_and_repository_boundaries():
    root = Path("apps/reader-android")

    assert (root / "settings.gradle.kts").exists()
    main = (
        root / "app/src/main/java/com/bookmd/reader/MainActivity.kt"
    ).read_text(encoding="utf-8")
    repo = (
        root / "app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "WebView" in main
    assert "BookRepository" in repo
    assert "book.json" in repo


def test_android_main_activity_destroys_webview_on_exit():
    main = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/MainActivity.kt"
    ).read_text(encoding="utf-8")

    assert "override fun onDestroy()" in main
    assert "webView.destroy()" in main
    assert "super.onDestroy()" in main


def test_android_main_activity_webview_uses_minimal_local_file_permissions():
    main = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/MainActivity.kt"
    ).read_text(encoding="utf-8")

    assert "webView.settings.javaScriptEnabled = true" in main
    assert "webView.settings.allowFileAccess = true" in main
    assert "webView.settings.allowContentAccess = false" in main
    assert "webView.settings.allowFileAccessFromFileURLs = false" in main
    assert "webView.settings.allowUniversalAccessFromFileURLs = false" in main


def test_android_main_activity_blocks_navigation_outside_renderer():
    main = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/MainActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.webkit.WebResourceRequest" in main
    assert "override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean" in main
    assert "return !isRendererUrl(request.url?.toString().orEmpty())" in main
    assert "override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean" in main
    assert "return !isRendererUrl(url)" in main
    assert "private fun isRendererUrl(url: String): Boolean" in main
    assert "Uri.parse(url).buildUpon().fragment(null).build().toString()" in main
    assert "return normalized == RENDERER_URL" in main
    assert "private const val RENDERER_URL = \"file:///android_asset/bookmd-renderer.html\"" in main


def test_android_reader_declares_first_phase_screen_boundaries():
    root = Path("apps/reader-android")
    manifest = (root / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    java_root = root / "app/src/main/java/com/bookmd/reader"

    assert "BookShelfActivity" in manifest
    assert "TocActivity" in manifest
    assert "ReaderActivity" in manifest
    assert (java_root / "BookShelfActivity.kt").exists()
    assert (java_root / "TocActivity.kt").exists()
    assert (java_root / "ReaderActivity.kt").exists()
    assert (java_root / "settings/ReaderSettings.kt").exists()


def test_android_manifest_exports_only_launcher_activity():
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )

    assert 'android:name=".BookShelfActivity"' in manifest
    assert 'android:exported="true"' in manifest
    internal_activities = [
        ".LogActivity",
        ".ImageViewerActivity",
        ".SourcePageActivity",
        ".SettingsActivity",
        ".SearchActivity",
        ".ReaderActivity",
        ".TocActivity",
        ".BookImportActivity",
        ".MainActivity",
    ]
    for activity in internal_activities:
        assert f'android:name="{activity}"' in manifest
        assert f'android:name="{activity}"\n            android:exported="false"' in manifest


def test_android_manifest_disables_system_backup_for_local_books():
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )

    assert 'android:allowBackup="false"' in manifest
    assert 'android:allowBackup="true"' not in manifest


def test_android_repository_models_manifest_and_chapters():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    repo = (root / "data/BookRepository.kt").read_text(encoding="utf-8")
    model = (root / "data/BookModels.kt").read_text(encoding="utf-8")

    assert "data class BookManifest" in model
    assert "data class BookChapter" in model
    assert "formatVersion: String?" in model
    assert 'optString("format_version")' in repo
    assert "readManifest" in repo
    assert "readChapterMarkdown" in repo


def test_android_shelf_ignores_hidden_import_temporary_book_dirs():
    repo = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "it.isDirectory" in repo
    assert "!it.name.startsWith(\".\")" in repo
    assert "File(it, \"book.json\").exists()" in repo


def test_android_asset_uses_bookmd_renderer_markdown_api():
    root = Path("apps/reader-android/app/src/main/assets")
    html = (root / "bookmd-renderer.html").read_text(encoding="utf-8")
    js = (root / "bookmd-renderer.js").read_text(encoding="utf-8")

    assert "bookmd-renderer.css" in html
    assert "bookmd-renderer.js" in html
    assert "window.BookMDReader" in js
    assert "renderMarkdown" in js
    assert "loadChapter" in js
    assert "jumpToBlock" in js
    assert "searchInChapter" in js


def test_android_reader_has_phase_two_local_reading_boundaries():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )

    assert "BookImportActivity" in manifest
    assert (root / "BookImportActivity.kt").exists()
    assert (root / "SearchActivity.kt").exists()
    assert (root / "data/SearchRepository.kt").exists()
    assert (root / "data/ReadingProgressStore.kt").exists()
    assert (root / "ui/SourceMapDialog.kt").exists()


def test_android_reader_wires_webview_bridge_for_source_and_images():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")

    assert "addJavascriptInterface" in reader
    assert "AndroidBookMD" in reader
    assert "onBlockSelected" in bridge
    assert "onImageSelected" in bridge
    assert "SourceMapDialog" in bridge


def test_android_source_map_repository_can_find_block():
    source_map = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SourceMapRepository.kt"
    ).read_text(encoding="utf-8")

    assert "findBlock" in source_map
    assert "block_id" in source_map
    assert "source_text" in source_map


def test_android_import_shelf_toc_reader_flow_is_wired():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    importer = (root / "BookImportActivity.kt").read_text(encoding="utf-8")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")
    toc = (root / "TocActivity.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")

    assert "Intent.ACTION_OPEN_DOCUMENT" in importer
    assert "onActivityResult" in importer
    assert "importBook" in importer
    assert "listBooks" in shelf
    assert "TocActivity" in shelf
    assert "readManifest" in toc
    assert "ReaderActivity" in toc
    assert "ScrollView" in toc
    assert "loadChapter" in reader
    assert "readChapterMarkdown" in reader
    assert "rewriteAssetPaths" in reader
    assert "jumpToBlock" in reader


def test_android_import_picker_hints_bookmd_archive_mime_types():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "type = \"*/*\"" in importer
    assert "putExtra(Intent.EXTRA_MIME_TYPES, BOOKMD_MIME_TYPES)" in importer
    assert "private val BOOKMD_MIME_TYPES = arrayOf(" in importer
    assert "\"application/zip\"" in importer
    assert "\"application/octet-stream\"" in importer


def test_android_import_repository_validates_bookmd_before_replacing_book():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "stagingDir" in repository
    assert "targetBackup" in repository
    assert "validateBook" in repository
    assert "canonicalFile" in repository
    assert "Invalid entry path" in repository
    assert "book.json is missing" in repository
    assert "chapter file is missing" in repository
    assert "renameTo(target)" in repository
    assert "deleteRecursively()" in repository


def test_android_book_repository_delete_is_limited_to_book_root_children():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "fun deleteBook(bookDir: File): Boolean" in repository
    assert "val root = rootDir.canonicalFile" in repository
    assert "val target = bookDir.canonicalFile" in repository
    assert "target.path == root.path" in repository
    assert "!target.path.startsWith(root.path + File.separator)" in repository
    assert "val manifest = File(target, \"book.json\")" in repository
    assert "!target.isDirectory || !manifest.exists()" in repository
    assert "target.deleteRecursively()" in repository


def test_android_import_repository_reports_corrupt_archives_and_missing_media():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "ZipException" in repository
    assert "Invalid BookMD archive" in repository
    assert "validateReferencedAssets" in repository
    assert "asset file is missing" in repository
    assert "../assets/" in repository


def test_android_import_repository_rejects_duplicate_archive_entries():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "val extractedPaths = mutableSetOf<String>()" in repository
    assert "require(extractedPaths.add(output.path))" in repository
    assert "duplicate entry path" in repository


def test_android_import_repository_validates_markdown_image_assets():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "ASSET_REFERENCE_PATTERN" in repository
    assert r"""src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))""" in repository
    assert "\\]\\(" in repository
    assert "match.groupValues[1]" in repository


def test_android_import_repository_validates_html_src_with_attribute_spacing():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert r"""src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))""" in repository


def test_android_import_repository_validates_html_src_case_insensitively_without_data_src():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "RegexOption.IGNORE_CASE" in repository
    assert r"""(?<![\w:-])src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))""" in repository


def test_android_import_repository_validates_unquoted_html_src_assets():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert r"""|(\.\./assets/[^\s>"']+)""" in repository
    assert "assetReferenceFromMatch(match)" in repository


def test_android_import_repository_decodes_html_src_entities_before_lookup():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "decodeHtmlAssetPath(source)" in repository
    assert "HTML_NAMED_ENTITY_PATTERN.replace" in repository
    assert "\"amp\" -> \"&\"" in repository
    assert "\"quot\" -> \"\\\"\"" in repository
    assert "val assetSource = if (isHtmlAssetReference(match)) decodeHtmlAssetPath(source) else source" in repository
    assert "Uri.decode(unescapeMarkdownAssetPath(assetSource.removePrefix(\"../\")))" in repository


def test_android_import_repository_decodes_html_entities_only_for_html_src_assets():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "isHtmlAssetReference(match)" in repository
    assert "if (isHtmlAssetReference(match)) decodeHtmlAssetPath(source) else source" in repository
    assert "Uri.decode(unescapeMarkdownAssetPath(assetSource.removePrefix(\"../\")))" in repository


def test_android_import_repository_decodes_numeric_html_src_entities_before_lookup():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "HTML_NUMERIC_ENTITY_PATTERN.replace" in repository
    assert r"""&#(?:x([0-9A-Fa-f]+)|([0-9]+));""" in repository
    assert "match.groupValues[1].toIntOrNull(16)" in repository
    assert "match.groupValues[2].toIntOrNull(10)" in repository
    assert "Character.toChars(codePoint).concatToString()" in repository


def test_android_import_repository_decodes_named_html_src_entities_case_insensitively():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "HTML_NAMED_ENTITY_PATTERN.replace" in repository
    assert r"""&(amp|quot|apos|lt|gt);""" in repository
    assert "RegexOption.IGNORE_CASE" in repository
    assert "match.groupValues[1].lowercase()" in repository


def test_android_import_repository_validates_markdown_asset_paths_with_spaces():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "assetReferenceFromMatch(match)" in repository
    assert "match.groupValues.drop(1).firstOrNull { it.isNotBlank() }" in repository
    assert r"""\]\((\.\./assets/(?:\\\)|[^)])*?)(\s+["'][^"']*["'])?\)""" in repository
    assert r"""src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))""" in repository
    assert "[^\"')\\s]+" not in repository


def test_android_import_repository_validates_angle_bracket_markdown_asset_paths():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert r"""\]\(<(\.\./assets/[^>]+)>(\s+["'][^"']*["'])?\)""" in repository
    assert "assetReferenceFromMatch(match)" in repository
    assert "match.groupValues.drop(1).firstOrNull { it.isNotBlank() }" in repository


def test_android_import_repository_validates_markdown_asset_paths_with_titles():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert r"""(\s+["'][^"']*["'])?""" in repository
    assert r"""\]\(<(\.\./assets/[^>]+)>(\s+["'][^"']*["'])?\)""" in repository
    assert r"""\]\((\.\./assets/(?:\\\)|[^)])*?)(\s+["'][^"']*["'])?\)""" in repository
    assert "assetReferenceFromMatch(match)" in repository


def test_android_import_repository_unescapes_markdown_asset_parentheses_before_lookup():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert r"""(?:\\\)|[^)])*?""" in repository
    assert "unescapeMarkdownAssetPath(assetSource.removePrefix(\"../\"))" in repository
    assert ".replace(\"\\\\(\", \"(\")" in repository
    assert ".replace(\"\\\\)\", \")\")" in repository


def test_android_import_repository_decodes_percent_encoded_asset_paths():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "import android.net.Uri" in repository
    assert "val assetPath = Uri.decode(unescapeMarkdownAssetPath(assetSource.removePrefix(\"../\")))" in repository
    assert "safeOutputFile(bookDir, assetPath)" in repository


def test_android_import_repository_rejects_decoded_asset_paths_outside_assets_root():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "val assetRoot = safeOutputFile(bookDir, \"assets\")" in repository
    assert "assetFile.path == assetRoot.path || assetFile.path.startsWith(assetRoot.path + File.separator)" in repository
    assert "require(isInsideAssets)" in repository
    assert "asset path is outside assets" in repository


def test_android_import_repository_rejects_malformed_chapter_entries():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/BookRepository.kt"
    ).read_text(encoding="utf-8")

    assert "chaptersJson.optJSONObject(index)" in repository
    assert "chapter entry is invalid" in repository


def test_android_import_ui_reports_failures_and_preserves_source_file_name():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "runCatching" in importer
    assert "Import failed:" in importer
    assert "OpenableColumns.DISPLAY_NAME" in importer
    assert "sanitizeImportName" in importer
    assert "copyUriToImportFile(uri, displayNameForUri(uri))" in importer


def test_android_import_ui_falls_back_when_display_name_is_blank():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "val displayNameColumn = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)" in importer
    assert "if (displayNameColumn >= 0)" in importer
    assert "val displayName = cursor.getString" in importer
    assert "if (!displayName.isNullOrBlank()) return displayName" in importer
    assert "getColumnIndexOrThrow(OpenableColumns.DISPLAY_NAME)" not in importer
    assert "uri.lastPathSegment?.substringAfterLast('/')" in importer
    assert "\"imported.bookmd\"" in importer


def test_android_import_ui_caps_temporary_file_name_length():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "MAX_IMPORT_CACHE_NAME_LENGTH" in importer
    assert "cleaned.endsWith(suffix, ignoreCase = true)" in importer
    assert "cleaned.dropLast(suffix.length)" in importer
    assert "base.take(MAX_IMPORT_CACHE_NAME_LENGTH - suffix.length)" in importer
    assert "return \"$cappedBase$suffix\"" in importer


def test_android_import_ui_deletes_cache_copy_after_import_attempt():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "var imported: File? = null" in importer
    assert "finally" in importer
    assert "imported?.delete()" in importer
    assert "repository.importBook(requireNotNull(imported))" in importer


def test_android_import_ui_returns_to_shelf_after_successful_import():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "finish()" in importer
    assert "status.text = \"Imported: ${bookDir.name}\"" in importer
    assert "logStore.append(\"import\", \"Imported ${bookDir.name}\")" in importer
    assert "onSuccess { bookDir ->" in importer
    assert "onFailure { error ->" in importer


def test_android_import_ui_deletes_partial_cache_copy_when_copy_fails():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "catch (error: Exception)" in importer
    assert "target.delete()" in importer
    assert "throw error" in importer


def test_android_import_ui_reports_when_no_file_is_selected():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "showNoFileSelected()" in importer
    assert "No file selected." in importer
    assert "resultCode != RESULT_OK" in importer
    assert "data?.data" in importer


def test_android_import_status_is_scrollable_on_phone_height():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.widget.ScrollView" in importer
    assert "private lateinit var statusScroll: ScrollView" in importer
    assert "statusScroll = ScrollView(this)" in importer
    assert "statusScroll.addView(status)" in importer
    assert "LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f)" in importer


def test_android_import_status_text_is_readable_on_phone():
    importer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookImportActivity.kt"
    ).read_text(encoding="utf-8")

    assert "status = TextView(this).apply" in importer
    assert "Choose a .bookmd package to import." in importer
    assert "textSize = 16f" in importer
    assert "setPadding(0, 24, 0, 24)" in importer


def test_android_device_smoke_can_verify_bad_import_does_not_replace_books():
    verifier = Path("scripts/verify_android_reader.py").read_text(encoding="utf-8")

    assert "--verify-bad-import" in verifier
    assert "_verify_bad_import_via_picker" in verifier
    assert "Import failed:" in verifier
    assert "CorruptBookmdSmoke.bookmd" in verifier
    assert "existing_title" in verifier


def test_android_shelf_opens_last_read_chapter_when_progress_exists():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")
    progress = (root / "data/ReadingProgressStore.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")

    assert "ReadingProgressStore" in shelf
    assert "readProgress(bookDir.name)" in shelf
    assert "ReaderActivity" in shelf
    assert "EXTRA_CHAPTER_PATH" in shelf
    assert "saveBookProgress" in progress
    assert "saveBookProgress(bookDir.name" in reader


def test_android_shelf_exposes_toc_entry_even_when_progress_restores_reader():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "text = \"TOC\"" in shelf
    assert "openToc(bookDir)" in shelf
    assert "private fun openToc(bookDir: File)" in shelf
    assert "Intent(this, TocActivity::class.java)" in shelf
    assert "putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)" in shelf


def test_android_shelf_shows_recent_progress_and_can_delete_books():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")
    progress = (root / "data/ReadingProgressStore.kt").read_text(encoding="utf-8")
    repository = (root / "data/BookRepository.kt").read_text(encoding="utf-8")

    assert "val updatedAtMillis: Long" in progress
    assert "System.currentTimeMillis()" in progress
    assert "updated_at" in progress
    assert "deleteBook" in repository
    assert "formatLastRead" in shelf
    assert "Last read:" in shelf
    assert "Scroll" in shelf
    assert "Delete" in shelf
    assert "repository.deleteBook(bookDir)" in shelf
    assert "refreshBooks()" in shelf


def test_android_delete_book_clears_saved_reading_progress():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")
    progress = (root / "data/ReadingProgressStore.kt").read_text(encoding="utf-8")

    assert "fun clearBookProgress(bookName: String)" in progress
    assert "preferences.all.keys" in progress
    assert "startsWith(\"$bookName:\")" in progress
    assert "progressStore.clearBookProgress(bookDir.name)" in shelf


def test_android_shelf_confirms_before_deleting_local_books():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.app.AlertDialog" in shelf
    assert "confirmDeleteBook(bookDir)" in shelf
    assert ".setTitle(\"Delete book?\")" in shelf
    assert ".setMessage(\"Delete ${displayBookName(bookDir)} from this device?\")" in shelf
    assert ".setPositiveButton(\"Delete\")" in shelf
    assert ".setNegativeButton(\"Cancel\", null)" in shelf
    assert "private fun deleteBook(bookDir: File)" in shelf
    assert "repository.deleteBook(bookDir)" in shelf


def test_android_reading_progress_ignores_bad_persisted_value_types():
    progress = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReadingProgressStore.kt"
    ).read_text(encoding="utf-8")

    assert "safeString(" in progress
    assert "safeInt(" in progress
    assert "safeLong(" in progress
    assert "runCatching" in progress
    assert "getOrDefault(default)" in progress


def test_android_reading_progress_normalizes_negative_persisted_values():
    progress = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReadingProgressStore.kt"
    ).read_text(encoding="utf-8")

    assert "private fun safeNonNegativeInt(key: String, default: Int): Int" in progress
    assert "safeInt(key, default).coerceAtLeast(0)" in progress
    assert "scrollY = safeNonNegativeInt(\"${bookId}:scroll_y\", 0)" in progress
    assert "scrollX = safeNonNegativeInt(\"${bookId}:scroll_x\", 0)" in progress
    assert "pageIndex = safePageIndex(\"${bookId}:page_index\", pageCount)" in progress
    assert "pageCount = safeNonNegativeInt(\"${bookId}:page_count\", 0)" in progress


def test_android_reading_progress_normalizes_persisted_page_index_to_page_count():
    progress = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReadingProgressStore.kt"
    ).read_text(encoding="utf-8")

    assert "val pageCount = safeNonNegativeInt(\"${bookId}:page_count\", 0)" in progress
    assert "pageIndex = safePageIndex(\"${bookId}:page_index\", pageCount)" in progress
    assert "private fun safePageIndex(key: String, pageCount: Int): Int" in progress
    assert "if (pageCount <= 0) return 0" in progress
    assert "safeNonNegativeInt(key, 0).coerceAtMost(pageCount - 1)" in progress


def test_android_shelf_shows_chapter_progress_summary():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "formatChapterProgress" in shelf
    assert "chapters.indexOfFirst { it.path == progress.chapterPath }" in shelf
    assert "Chapter ${chapterIndex + 1}/${chapters.size}" in shelf
    assert "Not started" in shelf


def test_android_shelf_flattens_recent_chapter_labels_from_bad_progress_state():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "displayProgressChapterName(progress.chapterPath)" in shelf
    assert "private fun displayProgressChapterName(chapterPath: String): String" in shelf
    assert ".replace(\"\\n\", \" \")" in shelf
    assert ".replace(\"\\r\", \" \")" in shelf


def test_android_shelf_book_list_is_scrollable_on_phone_height():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.widget.ScrollView" in shelf
    assert "private lateinit var listScroll: ScrollView" in shelf
    assert "listScroll = ScrollView(this)" in shelf
    assert "listScroll.addView(list)" in shelf
    assert "LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f)" in shelf


def test_android_shelf_empty_state_guides_first_import_readably():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "list.addView(emptyShelfText())" in shelf
    assert "private fun emptyShelfText(): TextView" in shelf
    assert "No local books yet. Import a .bookmd package to start reading." in shelf
    assert "textSize = 18f" in shelf
    assert "setPadding(0, 24, 0, 24)" in shelf


def test_android_shelf_truncates_long_book_and_progress_labels():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.text.TextUtils" in shelf
    assert "private fun TextView.applyShelfTextOverflow" in shelf
    assert "ellipsize = TextUtils.TruncateAt.END" in shelf
    assert "maxLines = lineLimit" in shelf
    assert "applyShelfTextOverflow()" in shelf


def test_android_shelf_flattens_book_titles_from_bad_metadata():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "displayBookTitle(manifest.title.ifBlank { bookDir.name })" in shelf
    assert "private fun displayBookTitle(title: String): String" in shelf
    assert ".replace(\"\\n\", \" \")" in shelf
    assert ".replace(\"\\r\", \" \")" in shelf


def test_android_shelf_flattens_book_directory_names_in_unavailable_and_delete_ui():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "displayBookName(bookDir)" in shelf
    assert "private fun displayBookName(bookDir: File): String" in shelf
    assert "displayBookTitle(bookDir.name)" in shelf
    assert "Book unavailable: ${displayBookName(bookDir)}" in shelf
    assert "Delete ${displayBookName(bookDir)} from this device?" in shelf


def test_android_shelf_delete_logs_use_flattened_book_names():
    shelf = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt"
    ).read_text(encoding="utf-8")

    assert "val bookName = displayBookName(bookDir)" in shelf
    assert '"Deleted $bookName"' in shelf
    assert '"Delete failed: $bookName"' in shelf
    assert '"Deleted ${bookDir.name}"' not in shelf
    assert '"Delete failed: ${bookDir.name}"' not in shelf


def test_android_reader_exposes_local_operation_logs():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")
    importer = (root / "BookImportActivity.kt").read_text(encoding="utf-8")
    log_store_path = root / "data/ReaderLogStore.kt"
    log_activity_path = root / "LogActivity.kt"

    assert "LogActivity" in manifest
    assert log_store_path.exists()
    assert log_activity_path.exists()

    log_store = log_store_path.read_text(encoding="utf-8")
    log_activity = log_activity_path.read_text(encoding="utf-8")

    assert "ReaderLogStore" in shelf
    assert "ReaderLogStore" in importer
    assert "Logs" in shelf
    assert "LogActivity" in shelf
    assert "logStore.append(\"import\"" in importer
    assert "logStore.append(" in shelf
    assert "\"delete\"" in shelf
    assert "fun entries()" in log_store
    assert "fun clear()" in log_store
    assert "bookmd_logs" in log_store
    assert "Clear logs" in log_activity
    assert "No logs yet." in log_activity


def test_android_operation_logs_show_entry_timestamps():
    log_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/LogActivity.kt"
    ).read_text(encoding="utf-8")

    assert "DateFormat.getDateTimeInstance" in log_activity
    assert "formatLogTime(entry.createdAtMillis)" in log_activity
    assert "Date(createdAtMillis)" in log_activity


def test_android_operation_logs_confirm_before_clearing():
    log_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/LogActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.app.AlertDialog" in log_activity
    assert "confirmClearLogs()" in log_activity
    assert ".setTitle(\"Clear logs?\")" in log_activity
    assert ".setMessage(\"Clear all local operation logs?\")" in log_activity
    assert ".setPositiveButton(\"Clear\")" in log_activity
    assert ".setNegativeButton(\"Cancel\", null)" in log_activity
    assert "private fun clearLogs()" in log_activity
    assert "logStore.clear()" in log_activity
    assert "refreshLogs()" in log_activity


def test_android_operation_logs_empty_state_is_readable():
    log_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/LogActivity.kt"
    ).read_text(encoding="utf-8")

    assert "list.addView(emptyLogText())" in log_activity
    assert "private fun emptyLogText(): TextView" in log_activity
    assert "No logs yet." in log_activity
    assert "textSize = 18f" in log_activity
    assert "setPadding(0, 24, 0, 24)" in log_activity


def test_android_operation_logs_disable_clear_button_when_empty():
    log_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/LogActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private lateinit var clearButton: Button" in log_activity
    assert "clearButton = Button(this@LogActivity).apply" in log_activity
    assert "clearButton.isEnabled = entries.isNotEmpty()" in log_activity


def test_android_operation_log_rows_truncate_long_messages_on_phone():
    log_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/LogActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.text.TextUtils" in log_activity
    assert "maxLines = MAX_LOG_ENTRY_LINES" in log_activity
    assert "ellipsize = TextUtils.TruncateAt.END" in log_activity
    assert "private const val MAX_LOG_ENTRY_LINES = 4" in log_activity


def test_android_operation_log_rows_flatten_multiline_messages_on_phone():
    log_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/LogActivity.kt"
    ).read_text(encoding="utf-8")

    assert "displayLogMessage(entry.message)" in log_activity
    assert "private fun displayLogMessage(message: String): String" in log_activity
    assert ".replace(\"\\n\", \" \")" in log_activity
    assert ".replace(\"\\r\", \" \")" in log_activity


def test_android_operation_log_rows_flatten_multiline_categories_on_phone():
    log_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/LogActivity.kt"
    ).read_text(encoding="utf-8")

    assert "displayLogCategory(entry.category)" in log_activity
    assert "private fun displayLogCategory(category: String): String" in log_activity
    assert "category.ifBlank { \"unknown\" }" in log_activity
    assert ".replace(\"\\n\", \" \")" in log_activity
    assert ".replace(\"\\r\", \" \")" in log_activity


def test_android_reader_logs_ignore_corrupt_persisted_log_json():
    log_store = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReaderLogStore.kt"
    ).read_text(encoding="utf-8")

    assert "readEntriesArray()" in log_store
    assert "runCatching" in log_store
    assert "getOrElse { JSONArray() }" in log_store
    assert "preferences.getString(KEY_ENTRIES, \"[]\")" in log_store


def test_android_reader_logs_skip_malformed_persisted_entries():
    log_store = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReaderLogStore.kt"
    ).read_text(encoding="utf-8")

    assert "entries.optJSONObject(index) ?: continue" in log_store
    assert "trimmed.put(entries.optJSONObject(index) ?: continue)" in log_store
    assert "item.optString(\"category\")" in log_store


def test_android_reader_logs_trim_long_messages_before_persisting():
    log_store = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/ReaderLogStore.kt"
    ).read_text(encoding="utf-8")

    assert "MAX_MESSAGE_LENGTH" in log_store
    assert ".put(\"message\", trimMessage(message))" in log_store
    assert "message.take(MAX_MESSAGE_LENGTH)" in log_store
    assert "message truncated" in log_store


def test_android_search_flow_jumps_to_reader_block():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    search = (root / "SearchActivity.kt").read_text(encoding="utf-8")
    repository = (root / "data/SearchRepository.kt").read_text(encoding="utf-8")

    assert "SearchRepository" in search
    assert "ReaderActivity" in search
    assert "EXTRA_TARGET_BLOCK_ID" in search
    assert "search_index.json" in repository
    assert "chapter_path" in repository


def test_android_search_results_include_context_and_keyword_highlight():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    search = (root / "SearchActivity.kt").read_text(encoding="utf-8")
    repository = (root / "data/SearchRepository.kt").read_text(encoding="utf-8")

    assert "val snippet: String" in repository
    assert "val matchStart: Int" in repository
    assert "val matchEnd: Int" in repository
    assert "buildSnippet" in repository
    assert "indexOf(normalizedQuery, ignoreCase = true)" in repository
    assert "SpannableString" in search
    assert "ForegroundColorSpan" in search
    assert "StyleSpan(Typeface.BOLD)" in search
    assert "renderHighlightedResult" in search
    assert "result.snippet" in search
    assert "Type a search term." in search
    assert "No results." in search


def test_android_search_screen_shows_initial_prompt_on_open():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "showInitialSearchPrompt()" in search
    assert "private fun showInitialSearchPrompt()" in search
    assert "results.addView(statusText(\"Type a search term.\"))" in search


def test_android_search_results_fall_back_for_blank_chapter_titles():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SearchRepository.kt"
    ).read_text(encoding="utf-8")

    assert "displayChapterTitle(item, chapterPath)" in repository
    assert "item.optString(\"chapter_title\").ifBlank" in repository
    assert "chapterPath.substringAfterLast('/')" in repository
    assert "item.optString(\"chapter_id\").ifBlank { \"Untitled chapter\" }" in repository


def test_android_search_index_missing_or_corrupt_file_is_non_fatal():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SearchRepository.kt"
    ).read_text(encoding="utf-8")
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "searchOrEmpty" in repository
    assert "runCatching" in repository
    assert "searchOrEmpty(trimmedQuery)" in search
    assert "No results." in search


def test_android_search_index_skips_malformed_entries():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SearchRepository.kt"
    ).read_text(encoding="utf-8")

    assert "items.optJSONObject(index) ?: continue" in repository
    assert "item.optString(\"text\")" in repository
    assert "val chapterPath = item.optString(\"chapter_path\")" in repository
    assert "if (chapterPath.isBlank()) continue" in repository


def test_android_search_index_skips_results_without_jump_targets():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SearchRepository.kt"
    ).read_text(encoding="utf-8")

    assert "val blockId = item.optString(\"block_id\")" in repository
    assert "if (blockId.isBlank()) continue" in repository
    assert "blockId = blockId" in repository


def test_android_search_index_skips_missing_or_unsafe_chapter_paths():
    repository = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SearchRepository.kt"
    ).read_text(encoding="utf-8")

    assert "if (!chapterFileExists(chapterPath)) continue" in repository
    assert "private fun chapterFileExists(chapterPath: String): Boolean" in repository
    assert "val root = bookDir.canonicalFile" in repository
    assert "val chapterFile = File(bookDir, chapterPath).canonicalFile" in repository
    assert "chapterFile.path == root.path || chapterFile.path.startsWith(root.path + File.separator)" in repository
    assert "chapterFile.exists() && chapterFile.isFile" in repository


def test_android_search_results_are_scrollable_on_phone_height():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.widget.ScrollView" in search
    assert "private lateinit var resultsScroll: ScrollView" in search
    assert "resultsScroll = ScrollView(this)" in search
    assert "resultsScroll.addView(results)" in search
    assert "LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f)" in search


def test_android_search_result_rows_truncate_long_titles_and_snippets():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.text.TextUtils" in search
    assert "maxLines = MAX_SEARCH_RESULT_LINES" in search
    assert "ellipsize = TextUtils.TruncateAt.END" in search
    assert "private const val MAX_SEARCH_RESULT_LINES = 4" in search


def test_android_search_result_rows_flatten_multiline_titles_and_snippets():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "flattenSearchRowText(result.chapterTitle)" in search
    assert "flattenSearchRowText(result.snippet)" in search
    assert "private fun flattenSearchRowText(text: String): String" in search
    assert ".replace(\"\\n\", \" \")" in search
    assert ".replace(\"\\r\", \" \")" in search


def test_android_search_limits_large_result_sets_for_phone_performance():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    repository = (root / "data/SearchRepository.kt").read_text(encoding="utf-8")
    search = (root / "SearchActivity.kt").read_text(encoding="utf-8")

    assert "MAX_SEARCH_RESULTS" in repository
    assert "if (results.size >= MAX_SEARCH_RESULTS) break" in repository
    assert "SearchRepository.MAX_SEARCH_RESULTS" in search
    assert "Showing first ${SearchRepository.MAX_SEARCH_RESULTS} results." in search


def test_android_search_rejects_overlong_queries_for_phone_performance():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    repository = (root / "data/SearchRepository.kt").read_text(encoding="utf-8")
    search = (root / "SearchActivity.kt").read_text(encoding="utf-8")

    assert "MAX_SEARCH_QUERY_LENGTH" in repository
    assert "if (normalizedQuery.length > MAX_SEARCH_QUERY_LENGTH) return emptyList()" in repository
    assert "SearchRepository.MAX_SEARCH_QUERY_LENGTH" in search
    assert "Search term is too long." in search


def test_android_search_input_caps_query_length_before_submit():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.text.InputFilter" in search
    assert "filters = arrayOf(InputFilter.LengthFilter(SearchRepository.MAX_SEARCH_QUERY_LENGTH))" in search


def test_android_search_keyboard_action_runs_search_on_phone():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.view.inputmethod.EditorInfo" in search
    assert "setSingleLine(true)" in search
    assert "imeOptions = EditorInfo.IME_ACTION_SEARCH" in search
    assert "setOnEditorActionListener" in search
    assert "actionId == EditorInfo.IME_ACTION_SEARCH" in search
    assert "renderResults(text.toString())" in search


def test_android_search_activity_uses_shared_intent_keys():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "getStringExtra(EXTRA_BOOK_DIR)" in search
    assert "putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)" in search
    assert "putExtra(EXTRA_CHAPTER_ID, result.chapterId)" in search
    assert "putExtra(EXTRA_CHAPTER_PATH, result.chapterPath)" in search
    assert "putExtra(EXTRA_TARGET_BLOCK_ID, result.blockId)" in search
    assert 'getStringExtra("book_dir")' not in search


def test_android_search_handles_missing_launch_extras_without_crashing():
    search = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SearchActivity.kt"
    ).read_text(encoding="utf-8")

    assert "showSearchUnavailable()" in search
    assert "Search unavailable." in search
    assert "bookDirPath.isNullOrBlank()" in search


def test_android_source_map_dialog_shows_page_bbox_and_text():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    source_map = (root / "data/SourceMapRepository.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")
    dialog = (root / "ui/SourceMapDialog.kt").read_text(encoding="utf-8")

    assert "SourcePageActivity" in manifest
    assert (root / "SourcePageActivity.kt").exists()
    assert "bbox" in source_map
    assert "sourcePage" in source_map
    assert "sourceText" in source_map
    assert "findBlock" in bridge
    assert "SourceMapDialog.show" in bridge
    assert "bbox" in bridge
    assert "EXTRA_SOURCE_PAGE" in dialog
    assert "EXTRA_SOURCE_BBOX" in dialog
    assert "Open PDF Page" in dialog
    assert "SourcePageActivity" in dialog


def test_android_source_map_missing_or_corrupt_file_is_non_fatal():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    source_map = (root / "data/SourceMapRepository.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")
    dialog = (root / "ui/SourceMapDialog.kt").read_text(encoding="utf-8")

    assert "runCatching" in bridge
    assert "findBlockOrNull" in source_map
    assert "No source text available." in dialog
    assert "Open PDF Page" in dialog


def test_android_source_map_ignores_blank_block_ids():
    source_map = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SourceMapRepository.kt"
    ).read_text(encoding="utf-8")

    assert "val requestedBlockId = blockId.trim()" in source_map
    assert "if (requestedBlockId.isBlank()) return null" in source_map
    assert "item.optString(\"block_id\") == requestedBlockId" in source_map


def test_android_source_map_dialog_truncates_long_source_text():
    dialog = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ui/SourceMapDialog.kt"
    ).read_text(encoding="utf-8")

    assert "MAX_SOURCE_TEXT_PREVIEW_LENGTH" in dialog
    assert "sourceTextPreview(block.sourceText)" in dialog
    assert "text.take(MAX_SOURCE_TEXT_PREVIEW_LENGTH)" in dialog
    assert "Source text truncated. Open PDF Page for full context." in dialog


def test_android_source_map_dialog_truncates_long_block_ids_in_title():
    dialog = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ui/SourceMapDialog.kt"
    ).read_text(encoding="utf-8")

    assert "sourceTitlePreview(blockId)" in dialog
    assert "MAX_SOURCE_TITLE_LENGTH" in dialog
    assert "normalized.take(MAX_SOURCE_TITLE_LENGTH)" in dialog
    assert ".setTitle(\"Source: $title\")" in dialog


def test_android_source_map_dialog_uses_fallback_for_blank_block_title():
    dialog = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ui/SourceMapDialog.kt"
    ).read_text(encoding="utf-8")

    assert "val title = sourceTitlePreview(blockId).ifBlank { \"Unknown block\" }" in dialog
    assert ".setTitle(\"Source: $title\")" in dialog


def test_android_source_map_dialog_flattens_block_title_preview():
    dialog = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ui/SourceMapDialog.kt"
    ).read_text(encoding="utf-8")

    assert "val normalized = blockId.trim()" in dialog
    assert ".replace(\"\\n\", \" \")" in dialog
    assert ".replace(\"\\r\", \" \")" in dialog
    assert "if (normalized.length <= MAX_SOURCE_TITLE_LENGTH) return normalized" in dialog
    assert "return normalized.take(MAX_SOURCE_TITLE_LENGTH) + \"...\"" in dialog


def test_android_source_map_dialog_uses_fallback_for_blank_source_text():
    dialog = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ui/SourceMapDialog.kt"
    ).read_text(encoding="utf-8")

    assert "val sourceText = sourceTextPreview(block.sourceText).ifBlank { \"No source text available.\" }" in dialog
    assert "BBox: ${block.bbox}\\n\\n$sourceText" in dialog


def test_android_source_map_dialog_uses_fallback_for_blank_block_type():
    dialog = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ui/SourceMapDialog.kt"
    ).read_text(encoding="utf-8")

    assert "val sourceType = block.type.ifBlank { \"unknown\" }" in dialog
    assert "Type: $sourceType" in dialog


def test_android_source_map_skips_malformed_block_entries():
    source_map = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/data/SourceMapRepository.kt"
    ).read_text(encoding="utf-8")

    assert "blocks.optJSONObject(index) ?: continue" in source_map
    assert "item.optString(\"block_id\")" in source_map
    assert "val sourcePage = item.optInt(\"source_page\")" in source_map
    assert "if (sourcePage < 1) continue" in source_map
    assert "val bbox = item.optJSONArray(\"bbox\") ?: continue" in source_map
    assert "if (bbox.length() != 4) continue" in source_map
    assert "if (!bboxIsValid(bbox)) continue" in source_map
    assert "bbox.optDouble(index)" in source_map
    assert "value.isFinite()" in source_map
    assert "val left = bbox.optDouble(0)" in source_map
    assert "val top = bbox.optDouble(1)" in source_map
    assert "val right = bbox.optDouble(2)" in source_map
    assert "val bottom = bbox.optDouble(3)" in source_map
    assert "return right > left && bottom > top" in source_map
    assert "bbox.toString()" in source_map


def test_android_source_page_activity_renders_original_pdf_page():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    keys = (root / "IntentKeys.kt").read_text(encoding="utf-8")
    source_page = (root / "SourcePageActivity.kt").read_text(encoding="utf-8")

    assert "EXTRA_SOURCE_PAGE" in keys
    assert "EXTRA_SOURCE_BBOX" in keys
    assert "PdfRenderer" in source_page
    assert "ParcelFileDescriptor" in source_page
    assert "source/original.pdf" in source_page
    assert "val pageIndex = sourcePage - 1" in source_page
    assert "SourcePageView" in source_page
    assert "parseBbox" in source_page
    assert "JSONArray" in source_page
    assert "drawRect" in source_page
    assert "Paint.Style.STROKE" in source_page


def test_android_source_page_activity_renders_pdf_pages_on_white_background():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "bitmap.eraseColor(Color.WHITE)" in source_page
    assert "page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)" in source_page


def test_android_source_page_activity_ignores_invalid_bbox_values():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "if (values.length() != 4) return null" in source_page
    assert "bboxValueOrNull(values, 0)" in source_page
    assert "bboxValueOrNull(values, 3)" in source_page
    assert "bboxValueOrNull(values: JSONArray, index: Int)" in source_page
    assert "value.isFinite()" in source_page
    assert "if (right <= left || bottom <= top) return null" in source_page


def test_android_source_page_activity_caps_large_pdf_page_bitmaps():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "pageRenderScale(page.width, page.height)" in source_page
    assert "MAX_SOURCE_PAGE_BITMAP_SIDE" in source_page
    assert "SOURCE_PAGE_BASE_RENDER_SCALE" in source_page
    assert "coerceAtMost(SOURCE_PAGE_BASE_RENDER_SCALE)" in source_page
    assert "Bitmap.createBitmap(renderWidth, renderHeight, Bitmap.Config.ARGB_8888)" in source_page
    assert "SourcePageRender(bitmap, renderScale)" in source_page


def test_android_source_page_activity_allows_horizontal_scroll_for_wide_pdf_pages():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.widget.HorizontalScrollView" in source_page
    assert "val horizontalScroll = HorizontalScrollView(this)" in source_page
    assert "val verticalScroll = ScrollView(this)" in source_page
    assert "horizontalScroll.addView(verticalScroll)" in source_page
    assert "SourcePageView(" in source_page


def test_android_source_page_activity_draws_bbox_with_actual_render_scale():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private val renderScale: Float" in source_page
    assert "SourcePageView(" in source_page
    assert "sourcePageRender.bitmap" in source_page
    assert "sourcePageRender.renderScale" in source_page
    assert "rect.left * renderScale" in source_page
    assert "rect.bottom * renderScale" in source_page
    assert "rect.left * 2f" not in source_page


def test_android_source_page_activity_scrolls_to_bbox_after_render():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "val parsedBbox = parseBbox(bbox)" in source_page
    assert "scrollToSourceBbox(horizontalScroll, verticalScroll, parsedBbox, sourcePageRender.renderScale)" in source_page
    assert "private fun scrollToSourceBbox(" in source_page
    assert "horizontalScroll.post" in source_page
    assert "(bbox.left * renderScale).roundToInt()" in source_page
    assert "(bbox.top * renderScale).roundToInt()" in source_page
    assert "horizontalScroll.scrollTo(scrollX, 0)" in source_page
    assert "verticalScroll.scrollTo(0, scrollY)" in source_page


def test_android_source_page_activity_scrolls_to_bbox_with_context_margin():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "SOURCE_BBOX_SCROLL_MARGIN_PX" in source_page
    assert "((bbox.left * renderScale).roundToInt() - SOURCE_BBOX_SCROLL_MARGIN_PX).coerceAtLeast(0)" in source_page
    assert "((bbox.top * renderScale).roundToInt() - SOURCE_BBOX_SCROLL_MARGIN_PX).coerceAtLeast(0)" in source_page


def test_android_source_page_activity_handles_corrupt_original_pdf():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "runCatching" in source_page
    assert "renderSourcePage" in source_page
    assert "showSourcePageError" in source_page
    assert "Original PDF unavailable." in source_page


def test_android_source_page_activity_uses_consistent_error_for_missing_original_pdf():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "if (!pdfFile.exists())" in source_page
    assert "showSourcePageError(\"Original PDF unavailable.\")" in source_page
    assert "Original PDF not found." not in source_page


def test_android_source_page_error_message_is_readable_on_phone():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.view.Gravity" in source_page
    assert "textSize = 18f" in source_page
    assert "setPadding(32, 32, 32, 32)" in source_page
    assert "gravity = Gravity.CENTER_VERTICAL" in source_page


def test_android_source_page_activity_closes_pdf_resources_on_render_failure():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "try {" in source_page
    assert "finally" in source_page
    assert "page.close()" in source_page
    assert "renderer.close()" in source_page
    assert "descriptor.close()" in source_page


def test_android_source_page_activity_recycles_rendered_bitmap_on_exit():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private var renderedBitmap: Bitmap? = null" in source_page
    assert "renderedBitmap = sourcePageRender.bitmap" in source_page
    assert "override fun onDestroy()" in source_page
    assert "renderedBitmap?.recycle()" in source_page
    assert "renderedBitmap = null" in source_page
    assert "super.onDestroy()" in source_page


def test_android_source_page_activity_handles_missing_launch_extras():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "bookDirPath.isNullOrBlank()" in source_page
    assert "showSourcePageError(\"Original PDF unavailable.\")" in source_page


def test_android_source_page_activity_rejects_invalid_source_page_numbers():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "if (sourcePage < 1 || sourcePage > renderer.pageCount)" in source_page
    assert "throw IllegalArgumentException(\"Invalid source page\")" in source_page
    assert ".coerceAtLeast(0).coerceAtMost(renderer.pageCount - 1)" not in source_page


def test_android_source_page_activity_uses_shared_intent_keys():
    source_page = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SourcePageActivity.kt"
    ).read_text(encoding="utf-8")

    assert "getStringExtra(EXTRA_BOOK_DIR)" in source_page
    assert "getIntExtra(EXTRA_SOURCE_PAGE, 1)" in source_page
    assert "getStringExtra(EXTRA_SOURCE_BBOX)" in source_page
    assert "getStringExtra(\"book_dir\")" not in source_page
    assert "getIntExtra(\"source_page\", 1)" not in source_page
    assert "getStringExtra(\"source_bbox\")" not in source_page


def test_android_reader_has_settings_screen_and_modes():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    settings = (root / "settings/ReaderSettings.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")

    assert "SettingsActivity" in manifest
    assert (root / "SettingsActivity.kt").exists()
    assert "fontSize" in settings
    assert "lineHeight" in settings
    assert "theme" in settings
    assert "layout" in settings
    assert "languageMode" in settings
    assert "reading_config.json" in reader


def test_android_settings_screen_can_reset_to_readable_defaults():
    settings_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SettingsActivity.kt"
    ).read_text(encoding="utf-8")

    assert "Reset Defaults" in settings_activity
    assert "ReaderSettings()" in settings_activity
    assert "settings = ReaderSettings()" in settings_activity
    assert "saveAndRender()" in settings_activity


def test_android_settings_reset_defaults_requires_confirmation():
    settings_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SettingsActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.app.AlertDialog" in settings_activity
    assert "confirmResetDefaults()" in settings_activity
    assert '.setTitle("Reset defaults?")' in settings_activity
    assert '.setMessage("Restore readable default settings?")' in settings_activity
    assert '.setPositiveButton("Reset")' in settings_activity
    assert '.setNegativeButton("Cancel", null)' in settings_activity


def test_android_reader_settings_ignore_bad_persisted_value_types():
    settings = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/settings/ReaderSettings.kt"
    ).read_text(encoding="utf-8")

    assert "safeInt(" in settings
    assert "safeString(" in settings
    assert "runCatching" in settings
    assert "getOrDefault(default)" in settings
    assert "safeString(prefs, KEY_LINE_HEIGHT, null)?.toDoubleOrNull()" in settings


def test_android_reader_settings_normalize_extreme_persisted_values():
    settings = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/settings/ReaderSettings.kt"
    ).read_text(encoding="utf-8")

    assert "fun normalized()" in settings
    assert "fontSize.coerceIn(MIN_FONT_SIZE, MAX_FONT_SIZE)" in settings
    assert "lineHeight.isFinite()" in settings
    assert "lineHeight.coerceIn(MIN_LINE_HEIGHT, MAX_LINE_HEIGHT)" in settings
    assert "normalizeChoice(theme, ALLOWED_THEMES, ReaderSettings().theme)" in settings
    assert "normalizeChoice(layout, ALLOWED_LAYOUTS, ReaderSettings().layout)" in settings
    assert "normalizeChoice(languageMode, ALLOWED_LANGUAGE_MODES, ReaderSettings().languageMode)" in settings
    assert ").normalized()" in settings


def test_android_settings_screen_is_scrollable_on_phone_height():
    settings_activity = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/SettingsActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.widget.ScrollView" in settings_activity
    assert "setContentView(" in settings_activity
    assert "ScrollView(this).apply" in settings_activity
    assert "addView(LinearLayout(this@SettingsActivity).apply" in settings_activity


def test_android_reader_has_image_viewer_for_media_taps():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    manifest = Path("apps/reader-android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")
    viewer = (root / "ImageViewerActivity.kt").read_text(encoding="utf-8")

    assert "ImageViewerActivity" in manifest
    assert (root / "ImageViewerActivity.kt").exists()
    assert "onImageSelected" in bridge
    assert "EXTRA_MEDIA_URI" in bridge or "media_uri" in bridge
    assert "WebView" in viewer
    assert "loadDataWithBaseURL" in viewer


def test_android_image_viewer_handles_missing_media_uri_with_visible_message():
    viewer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ImageViewerActivity.kt"
    ).read_text(encoding="utf-8")

    assert "Media unavailable." in viewer
    assert "mediaUri.isBlank()" in viewer
    assert "bookmd-media-missing" in viewer
    assert "<img src=" in viewer


def test_android_visual_asset_smoke_uses_debug_only_bookshelf_dispatch():
    shelf = Path("apps/reader-android/app/src/main/java/com/bookmd/reader/BookShelfActivity.kt").read_text(
        encoding="utf-8"
    )

    assert "SMOKE_VISUAL_ASSET" in shelf
    assert "override fun onNewIntent" in shelf
    assert "BuildConfig.DEBUG" in shelf
    assert "ImageViewerActivity::class.java" in shelf
    assert "finish()" in shelf


def test_android_image_viewer_destroys_webview_on_exit():
    viewer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ImageViewerActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private lateinit var webView: WebView" in viewer
    assert "override fun onDestroy()" in viewer
    assert "webView.destroy()" in viewer
    assert "super.onDestroy()" in viewer


def test_android_image_viewer_supports_zooming_technical_figures():
    viewer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ImageViewerActivity.kt"
    ).read_text(encoding="utf-8")

    assert "settings.setSupportZoom(true)" in viewer
    assert "settings.builtInZoomControls = true" in viewer
    assert "settings.displayZoomControls = false" in viewer
    assert "settings.useWideViewPort = true" in viewer
    assert "settings.loadWithOverviewMode = true" in viewer


def test_android_image_viewer_keeps_technical_figures_accessible_and_contained():
    viewer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ImageViewerActivity.kt"
    ).read_text(encoding="utf-8")

    assert """<img src="$safeUri" alt="Book media">""" in viewer
    assert "object-fit: contain;" in viewer


def test_android_image_viewer_uses_white_background_for_transparent_technical_figures():
    viewer = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ImageViewerActivity.kt"
    ).read_text(encoding="utf-8")

    assert "setBackgroundColor(android.graphics.Color.WHITE)" in viewer
    assert "background: #fff;" in viewer
    assert "color: #111;" in viewer
    assert "background: #000;" not in viewer


def test_android_image_viewer_rejects_media_paths_outside_book_assets():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    viewer = (root / "ImageViewerActivity.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")

    assert "putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)" in bridge
    assert "normalizeMediaUri(rawMediaUri, bookDirPath)" in viewer
    assert "Uri.parse(mediaUri)" in viewer
    assert "uri.scheme != \"file\"" in viewer
    assert "File(bookDirPath, \"assets\").canonicalFile" in viewer
    assert "mediaFile.path == assetRoot.path || mediaFile.path.startsWith(assetRoot.path + File.separator)" in viewer
    assert "settings.allowContentAccess = false" in viewer
    assert "settings.allowFileAccessFromFileURLs = false" in viewer
    assert "settings.allowUniversalAccessFromFileURLs = false" in viewer


def test_android_reader_rewrites_only_safe_existing_asset_paths():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "rewriteSafeMarkdownLine(line)" in reader
    assert "rewriteSafeMarkdownSegment(segment)" in reader
    assert "rewriteMarkdownAssetPaths(segment)" in reader
    assert "rewriteHtmlAssetSrcValues(rewrittenMarkdownAssets)" in reader
    assert "File(bookDir, \"assets\").canonicalFile" in reader
    assert "assetFile.path == assetRoot.path || assetFile.path.startsWith(assetRoot.path + File.separator)" in reader
    assert "assetFile.toURI().toString()" in reader
    assert "webView.settings.allowContentAccess = false" in reader
    assert "webView.settings.allowFileAccessFromFileURLs = false" in reader
    assert "webView.settings.allowUniversalAccessFromFileURLs = false" in reader
    assert "markdown.replace(\"../assets/\", assetBase)" not in reader


def test_android_reader_rewrites_html_src_with_attribute_spacing():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert r"""src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))""" in reader
    assert r"""src\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>"']+))""" in reader
    assert "src=\\\"$safeUri\\\"" in reader


def test_android_reader_rewrites_html_src_case_insensitively_without_data_src():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "RegexOption.IGNORE_CASE" in reader
    assert r"""(?<![\w:-])src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))""" in reader
    assert r"""(?<![\w:-])src\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>"']+))""" in reader


def test_android_reader_rewrites_unquoted_html_src_assets():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert r"""|(\.\./assets/[^\s>"']+)""" in reader
    assert r"""|([^\s>"']+)""" in reader
    assert "htmlAssetSourceFromMatch(match)" in reader
    assert "mediaSourceFromMatch(match)" in reader
    assert "src=\\\"$safeUri\\\"" in reader


def test_android_reader_decodes_html_src_entities_before_lookup():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "decodeHtmlAssetPath(source)" in reader
    assert "HTML_NAMED_ENTITY_PATTERN.replace" in reader
    assert "\"amp\" -> \"&\"" in reader
    assert "\"quot\" -> \"\\\"\"" in reader
    assert "safeAssetUri(decodeHtmlAssetPath(source).removePrefix(\"../assets/\"))" in reader
    assert "safeMediaUri(decodeHtmlAssetPath(mediaSourceFromMatch(match)))" in reader


def test_android_reader_decodes_numeric_html_src_entities_before_lookup():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "HTML_NUMERIC_ENTITY_PATTERN.replace" in reader
    assert r"""&#(?:x([0-9A-Fa-f]+)|([0-9]+));""" in reader
    assert "match.groupValues[1].toIntOrNull(16)" in reader
    assert "match.groupValues[2].toIntOrNull(10)" in reader
    assert "Character.toChars(codePoint).concatToString()" in reader


def test_android_reader_decodes_named_html_src_entities_case_insensitively():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "HTML_NAMED_ENTITY_PATTERN.replace" in reader
    assert r"""&(amp|quot|apos|lt|gt);""" in reader
    assert "RegexOption.IGNORE_CASE" in reader
    assert "match.groupValues[1].lowercase()" in reader


def test_android_reader_rewrites_markdown_asset_paths_with_spaces_without_truncating():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "MARKDOWN_ASSET_PATH_PATTERN.replace(segment)" in reader
    assert "val source = match.groupValues[1]" in reader
    assert "safeAssetUri(assetPath)" in reader
    assert r"""\]\((\.\./assets/(?:\\\)|[^)])*?)(\s+["'][^"']*["'])?\)""" in reader
    assert r"""\.\./assets/([^\s)"']+)""" not in reader


def test_android_reader_rewrites_angle_bracket_markdown_asset_paths():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "ANGLE_MARKDOWN_ASSET_PATH_PATTERN.replace(segment)" in reader
    assert r"""\]\(<(\.\./assets/[^>]+)>(\s+["'][^"']*["'])?\)""" in reader
    assert "val rewrittenAngleAssets =" in reader
    assert "]($safeUri$title)" in reader


def test_android_reader_rewrites_markdown_asset_paths_with_titles():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert r"""\]\(<(\.\./assets/[^>]+)>(\s+["'][^"']*["'])?\)""" in reader
    assert r"""\]\((\.\./assets/(?:\\\)|[^)])*?)(\s+["'][^"']*["'])?\)""" in reader
    assert "val title = match.groupValues[2]" in reader
    assert "]($safeUri$title)" in reader


def test_android_reader_does_not_decode_html_entities_in_markdown_asset_paths():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    markdown_match_body = reader.split("private fun rewriteMarkdownAssetMatch(match: MatchResult): String", 1)[1]
    markdown_match_body = markdown_match_body.split("private fun unescapeMarkdownAssetPath", 1)[0]
    assert "decodeHtmlAssetPath" not in markdown_match_body


def test_android_reader_drops_markdown_asset_title_when_asset_is_missing():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "if (safeUri.isBlank()) return \"]()\"" in reader
    assert "return \"]($safeUri$title)\"" in reader


def test_android_reader_unescapes_markdown_asset_parentheses_before_lookup():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert r"""(?:\\\)|[^)])*?""" in reader
    assert "unescapeMarkdownAssetPath(source.removePrefix(\"../assets/\"))" in reader
    assert ".replace(\"\\\\(\", \"(\")" in reader
    assert ".replace(\"\\\\)\", \")\")" in reader


def test_android_reader_decodes_percent_encoded_asset_paths_before_lookup():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "val decodedAssetPath = Uri.decode(assetPath)" in reader
    assert "File(assetRoot, decodedAssetPath).canonicalFile" in reader
    assert "assetFile.path == assetRoot.path || assetFile.path.startsWith(assetRoot.path + File.separator)" in reader


def test_android_reader_strips_unsafe_inline_media_src_values():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "rewriteSafeMarkdownLine(line)" in reader
    assert "MEDIA_SRC_PATTERN.replace(rewrittenHtmlAssets)" in reader
    assert "safeMediaUri(decodeHtmlAssetPath(mediaSourceFromMatch(match)))" in reader
    assert "private fun safeMediaUri(mediaUri: String): String" in reader
    assert "Uri.parse(mediaUri)" in reader
    assert "if (uri.scheme != \"file\") return \"\"" in reader
    assert "File(uri.path ?: return \"\").canonicalFile" in reader
    assert "mediaFile.path == assetRoot.path || mediaFile.path.startsWith(assetRoot.path + File.separator)" in reader
    assert "private val MEDIA_SRC_PATTERN = Regex" in reader


def test_android_reader_does_not_rewrite_media_src_inside_code_fences():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "var inCodeFence = false" in reader
    assert "isCodeFenceDelimiter(line)" in reader
    assert "inCodeFence = !inCodeFence" in reader
    assert "if (inCodeFence) line else rewriteSafeMarkdownLine(line)" in reader


def test_android_reader_does_not_rewrite_media_src_inside_tilde_code_fences():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private fun isCodeFenceDelimiter(line: String): Boolean" in reader
    assert "val trimmed = line.trimStart()" in reader
    assert "trimmed.startsWith(\"```\") || trimmed.startsWith(\"~~~\")" in reader


def test_android_reader_does_not_rewrite_media_src_inside_inline_code_spans():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "var inlineCodeDelimiterLength = 0" in reader
    assert "inlineCodeDelimiterLength > 0" in reader
    assert "if (line[index] == '`')" in reader
    assert "val delimiterLength = countBacktickRun(line, index)" in reader
    assert "private fun countBacktickRun(line: String, start: Int): Int" in reader
    assert "private fun rewriteSafeMarkdownSegment(segment: String): String" in reader


def test_android_reader_does_not_rewrite_media_src_inside_multi_backtick_inline_code_spans():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "if (inlineCodeDelimiterLength == 0)" in reader
    assert "inlineCodeDelimiterLength = delimiterLength" in reader
    assert "else if (delimiterLength == inlineCodeDelimiterLength)" in reader
    assert "inlineCodeDelimiterLength = 0" in reader


def test_android_reader_blocks_non_file_webview_navigation():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.webkit.WebResourceRequest" in reader
    assert "override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean" in reader
    assert "return !isReaderRendererUrl(request.url?.toString().orEmpty())" in reader
    assert "override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean" in reader
    assert "return !isReaderRendererUrl(url)" in reader
    assert "private fun isReaderRendererUrl(url: String): Boolean" in reader
    assert "Uri.parse(url).buildUpon().fragment(null).build().toString()" in reader
    assert "return normalized == READER_RENDERER_URL" in reader
    assert "private const val READER_RENDERER_URL = \"file:///android_asset/bookmd-renderer.html\"" in reader


def test_android_reader_persists_reading_progress():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    progress = (root / "data/ReadingProgressStore.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")
    js = Path(
        "packages/markdown_renderer/renderer/bookmd-renderer.js"
    ).read_text(encoding="utf-8")

    assert "saveProgress" in progress
    assert "readProgress" in progress
    assert "currentProgress" in js
    assert "restoreProgress" in js
    assert "reportProgress" in js
    assert "addEventListener(\"scroll\"" in js
    assert "ReadingProgressStore" in reader
    assert "onReadingProgressChanged" in bridge
    assert "ReadingProgress(" in reader


def test_android_reader_exposes_basic_navigation_controls():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "Button" in reader
    assert "TOC" in reader
    assert "Search" in reader
    assert "Settings" in reader
    assert "Prev" in reader
    assert "Next" in reader
    assert "openAdjacentChapter" in reader
    assert "readManifestOrNull(bookDir)" in reader
    assert "TocActivity" in reader
    assert "SearchActivity" in reader
    assert "SettingsActivity" in reader


def test_android_reader_adjacent_navigation_ignores_unknown_current_chapter():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "val currentIndex = chapters.indexOfFirst { it.path == chapterPath }" in reader
    assert "if (currentIndex < 0) return" in reader
    assert "chapters.getOrNull(currentIndex + offset)" in reader


def test_android_reader_disables_adjacent_navigation_buttons_at_chapter_edges():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "isEnabled = hasAdjacentChapter(-1)" in reader
    assert "isEnabled = hasAdjacentChapter(1)" in reader
    assert "private fun hasAdjacentChapter(offset: Int): Boolean" in reader
    assert "val currentIndex = chapters.indexOfFirst { it.path == chapterPath }" in reader
    assert "return currentIndex >= 0 && chapters.getOrNull(currentIndex + offset) != null" in reader


def test_android_reader_toolbar_splits_controls_across_rows_for_phone_width():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "readerToolbarRow" in reader
    assert "addView(readerToolbarRow(\"TOC\", \"Prev\", \"Next\"))" in reader
    assert "addView(readerToolbarRow(\"Search\", \"Settings\"))" in reader


def test_android_toc_highlights_current_chapter_and_truncates_long_titles():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    keys = (root / "IntentKeys.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")
    toc = (root / "TocActivity.kt").read_text(encoding="utf-8")

    assert "EXTRA_CURRENT_CHAPTER_PATH" in keys
    assert "putExtra(EXTRA_CURRENT_CHAPTER_PATH, chapterPath)" in reader
    assert "ReadingProgressStore" in toc
    assert "currentChapterPath" in toc
    assert "chapter.path == currentChapterPath" in toc
    assert "setTypeface(typeface, Typeface.BOLD)" in toc
    assert "setBackgroundColor" in toc
    assert "ellipsize = TextUtils.TruncateAt.END" in toc
    assert "maxLines = 2" in toc


def test_android_toc_scrolls_current_chapter_into_view_on_long_books():
    toc = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/TocActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private var currentChapterRow: TextView? = null" in toc
    assert "val scrollView = ScrollView(this)" in toc
    assert "scrollCurrentChapterIntoView(scrollView)" in toc
    assert "private fun scrollCurrentChapterIntoView(scrollView: ScrollView)" in toc
    assert "currentChapterRow ?: return" in toc
    assert "scrollView.post" in toc
    assert "smoothScrollTo(0, (row.top - CURRENT_CHAPTER_SCROLL_MARGIN_PX).coerceAtLeast(0))" in toc
    assert "currentChapterRow = this" in toc


def test_android_toc_falls_back_for_blank_book_and_chapter_titles():
    toc = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/TocActivity.kt"
    ).read_text(encoding="utf-8")

    assert "displayBookTitle(manifest)" in toc
    assert "manifest.title.ifBlank { bookDir.name }" in toc
    assert "displayChapterTitle(chapter)" in toc
    assert "chapter.title.ifBlank" in toc
    assert "chapter.path.substringAfterLast('/')" in toc
    assert "\"Untitled chapter\"" in toc


def test_android_toc_flattens_book_and_chapter_titles_from_bad_metadata():
    toc = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/TocActivity.kt"
    ).read_text(encoding="utf-8")

    assert "flattenDisplayTitle(manifest.title.ifBlank { bookDir.name })" in toc
    assert "flattenDisplayTitle(chapter.title.ifBlank" in toc
    assert "private fun flattenDisplayTitle(title: String): String" in toc
    assert ".replace(\"\\n\", \" \")" in toc
    assert ".replace(\"\\r\", \" \")" in toc


def test_android_toc_and_shelf_handle_unreadable_manifest_without_crashing():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    repository = (root / "data/BookRepository.kt").read_text(encoding="utf-8")
    toc = (root / "TocActivity.kt").read_text(encoding="utf-8")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")

    assert "readManifestOrNull" in repository
    assert "runCatching" in repository
    assert "readManifestOrNull(bookDir)" in toc
    assert "Book unavailable." in toc
    assert "No chapters available." in toc
    assert "readManifestOrNull(bookDir)" in shelf
    assert "Book unavailable:" in shelf


def test_android_toc_and_search_unavailable_messages_are_readable_on_phone():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    toc = (root / "TocActivity.kt").read_text(encoding="utf-8")
    search = (root / "SearchActivity.kt").read_text(encoding="utf-8")

    assert "import android.view.Gravity" in toc
    assert "gravity = Gravity.CENTER_VERTICAL" in toc
    assert "import android.view.Gravity" in search
    assert "gravity = Gravity.CENTER_VERTICAL" in search


def test_android_toc_handles_missing_launch_extras_without_crashing():
    toc = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/TocActivity.kt"
    ).read_text(encoding="utf-8")

    assert "bookDirPath.isNullOrBlank()" in toc
    assert "Book unavailable." in toc
    assert "return" in toc


def test_android_reader_reloads_settings_after_returning_from_settings():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "override fun onResume()" in reader
    assert "val updatedSettings = ReaderSettings.load(this, readBookDefaultsOrDefault())" in reader
    assert "updatedSettings != settings" in reader
    assert "settings = updatedSettings" in reader
    assert "loadChapter()" in reader


def test_android_reader_cleans_up_progress_callbacks_and_webview_on_destroy():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "override fun onDestroy()" in reader
    assert "flushPendingProgress()" in reader
    assert "progressHandler.removeCallbacks(progressFlushRunnable)" in reader
    assert "webView.destroy()" in reader
    assert "super.onDestroy()" in reader


def test_android_reader_handles_missing_chapter_file_without_crashing():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    repository = (root / "data/BookRepository.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")

    assert "readChapterMarkdownOrNull" in reader
    assert "runCatching { readChapterMarkdown(bookDir, chapterPath) }" in repository
    assert "chapterUnavailableMarkdown" in reader
    assert "Chapter unavailable" in reader
    assert "readManifestOrNull(bookDir)" in reader


def test_android_reader_escapes_missing_chapter_path_in_fallback_markdown():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "safeMarkdownInlineCodeText(path.ifBlank { \"unknown chapter\" })" in reader
    assert "private fun safeMarkdownInlineCodeText(text: String): String" in reader
    assert ".replace(\"`\", \"'\")" in reader
    assert "Unable to open `$safePath`." in reader


def test_android_reader_flattens_missing_chapter_path_in_fallback_markdown():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert ".replace(\"\\n\", \" \")" in reader
    assert ".replace(\"\\r\", \" \")" in reader


def test_android_reader_rejects_legacy_chapter_paths_outside_book_dir():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    repository = (root / "data/BookRepository.kt").read_text(encoding="utf-8")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")

    assert "safeOutputFile(bookDir, chapter.path).readText()" in repository
    assert "safeOutputFile(bookDir, chapterPath).readText()" in repository
    assert "fun chapterFileExists(bookDir: File, chapterPath: String): Boolean" in repository
    assert "repository.chapterFileExists(bookDir, lastChapter.path)" in shelf
    assert "File(bookDir, lastChapter.path).exists()" not in shelf


def test_android_reader_handles_missing_launch_extras_without_crashing():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "showReaderUnavailable()" in reader
    assert "Reader unavailable." in reader
    assert "bookDirPath.isNullOrBlank()" in reader
    assert "requestedChapterPath.isNullOrBlank()" in reader


def test_android_reader_unavailable_message_is_readable_on_phone():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "import android.view.Gravity" in reader
    assert "textSize = 18f" in reader
    assert "setPadding(32, 32, 32, 32)" in reader
    assert "gravity = Gravity.CENTER_VERTICAL" in reader


def test_android_reader_bad_reading_config_falls_back_to_defaults():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "readBookDefaultsOrDefault" in reader
    assert "runCatching" in reader
    assert "ReaderSettings()" in reader
    assert "ReaderSettings.load(this, readBookDefaultsOrDefault())" in reader


def test_android_reader_throttles_scroll_progress_writes():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "Handler(Looper.getMainLooper())" in reader
    assert "pendingProgress" in reader
    assert "progressFlushRunnable" in reader
    assert "scheduleProgressFlush()" in reader
    assert "flushPendingProgress()" in reader
    assert "removeCallbacks(progressFlushRunnable)" in reader
    assert "postDelayed(progressFlushRunnable, PROGRESS_FLUSH_DELAY_MS)" in reader
    assert "private const val PROGRESS_FLUSH_DELAY_MS" in reader


def test_android_reader_persists_paged_progress_state():
    root = Path("apps/reader-android/app/src/main/java/com/bookmd/reader")
    progress = (root / "data/ReadingProgressStore.kt").read_text(encoding="utf-8")
    reader = (root / "ReaderActivity.kt").read_text(encoding="utf-8")
    bridge = (root / "web/BookMdWebBridge.kt").read_text(encoding="utf-8")
    shelf = (root / "BookShelfActivity.kt").read_text(encoding="utf-8")

    assert "val scrollX: Int" in progress
    assert "val pageIndex: Int" in progress
    assert "val pageCount: Int" in progress
    assert "scroll_x" in progress
    assert "page_index" in progress
    assert "page_count" in progress
    assert "onReadingProgressChangedPayload" in bridge
    assert "JSONObject(payload ?: \"{}\")" in bridge
    assert ".put(\"scroll_x\", progress.scrollX)" in reader
    assert ".put(\"page_index\", progress.pageIndex)" in reader
    assert ".put(\"page_count\", progress.pageCount)" in reader
    assert "progress.optInt(\"scroll_x\", 0)" in reader
    assert "progress.optInt(\"page_index\", 0)" in reader
    assert "formatPageProgress" in shelf


def test_android_reader_normalizes_negative_progress_values_from_bridge():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private fun nonNegativeProgressValue(value: Int): Int" in reader
    assert "value.coerceAtLeast(0)" in reader
    assert "scrollY = nonNegativeProgressValue(progress.optInt(\"scroll_y\", 0))" in reader
    assert "scrollX = nonNegativeProgressValue(progress.optInt(\"scroll_x\", 0))" in reader
    assert "pageIndex = normalizedPageIndex(progress.optInt(\"page_index\", 0), pageCount)" in reader
    assert "pageCount = nonNegativeProgressValue(progress.optInt(\"page_count\", 0))" in reader
    assert "scrollY = nonNegativeProgressValue(scrollY)" in reader
    assert "scrollX = nonNegativeProgressValue(scrollX)" in reader
    assert "pageIndex = normalizedPageIndex(pageIndex, normalizedPageCount)" in reader
    assert "pageCount = normalizedPageCount" in reader


def test_android_reader_normalizes_page_index_to_page_count_from_bridge():
    reader = Path(
        "apps/reader-android/app/src/main/java/com/bookmd/reader/ReaderActivity.kt"
    ).read_text(encoding="utf-8")

    assert "private fun normalizedPageIndex(pageIndex: Int, pageCount: Int): Int" in reader
    assert "if (pageCount <= 0) return 0" in reader
    assert "nonNegativeProgressValue(pageIndex).coerceAtMost(pageCount - 1)" in reader
    assert "val pageCount = nonNegativeProgressValue(progress.optInt(\"page_count\", 0))" in reader
    assert "pageIndex = normalizedPageIndex(progress.optInt(\"page_index\", 0), pageCount)" in reader
    assert "val normalizedPageCount = nonNegativeProgressValue(pageCount)" in reader
    assert "pageIndex = normalizedPageIndex(pageIndex, normalizedPageCount)" in reader
    assert "pageCount = normalizedPageCount" in reader
