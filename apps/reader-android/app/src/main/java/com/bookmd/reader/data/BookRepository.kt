package com.bookmd.reader.data

import android.net.Uri
import java.io.File
import java.util.zip.ZipFile
import java.util.zip.ZipException
import org.json.JSONObject

class BookRepository(private val rootDir: File) {
    fun listBooks(): List<File> {
        return rootDir.listFiles()
            ?.filter { it.isDirectory && !it.name.startsWith(".") && File(it, "book.json").exists() }
            ?.sortedBy { it.name.lowercase() }
            ?: emptyList()
    }

    fun importBook(bookmd: File): File {
        rootDir.mkdirs()
        val target = File(rootDir, safeBookDirName(bookmd.nameWithoutExtension))
        val staging = stagingDir(target)
        val backup = targetBackup(target)
        staging.deleteRecursively()
        backup.deleteRecursively()

        try {
            extractBook(bookmd, staging)
            validateBook(staging)
            if (target.exists() && !target.renameTo(backup)) {
                error("Unable to prepare existing book for replacement")
            }
            if (!staging.renameTo(target)) {
                if (backup.exists()) backup.renameTo(target)
                error("Unable to finalize import")
            }
            backup.deleteRecursively()
            return target
        } catch (error: Exception) {
            staging.deleteRecursively()
            if (!target.exists() && backup.exists()) {
                backup.renameTo(target)
            }
            throw error
        } finally {
            if (target.exists()) {
                backup.deleteRecursively()
            }
        }
    }

    private fun extractBook(bookmd: File, targetDir: File) {
        targetDir.mkdirs()
        try {
            ZipFile(bookmd).use { zip ->
                val extractedPaths = mutableSetOf<String>()
                zip.entries().asSequence().forEach { entry ->
                    val output = safeOutputFile(targetDir, entry.name)
                    require(extractedPaths.add(output.path)) {
                        "duplicate entry path: ${entry.name}"
                    }
                    if (entry.isDirectory) {
                        output.mkdirs()
                    } else {
                        output.parentFile?.mkdirs()
                        zip.getInputStream(entry).use { input ->
                            output.outputStream().use { input.copyTo(it) }
                        }
                    }
                }
            }
        } catch (error: ZipException) {
            throw IllegalArgumentException("Invalid BookMD archive", error)
        }
    }

    private fun validateBook(bookDir: File) {
        require(File(bookDir, "book.json").exists()) { "book.json is missing" }
        val manifest = readManifest(bookDir)
        manifest.formatVersion?.let { formatVersion ->
            val major = formatVersion.substringBefore('.')
            require(major == "1") {
                "Unsupported BookMD format major version: $formatVersion"
            }
        }
        require(manifest.chapters.isNotEmpty()) { "book chapters are missing" }
        manifest.chapters.forEach { chapter ->
            require(chapter.path.isNotBlank()) { "chapter path is missing" }
            val chapterFile = safeOutputFile(bookDir, chapter.path)
            require(chapterFile.exists() && chapterFile.isFile) {
                "chapter file is missing: ${chapter.path}"
            }
            validateReferencedAssets(bookDir, chapterFile)
        }
    }

    private fun validateReferencedAssets(bookDir: File, chapterFile: File) {
        val assetRoot = safeOutputFile(bookDir, "assets")
        chapterFile.forEachLine { line ->
            ASSET_REFERENCE_PATTERN.findAll(line).forEach { match ->
                val source = assetReferenceFromMatch(match) ?: return@forEach
                if (!source.startsWith("../assets/")) return@forEach
                val assetSource = if (isHtmlAssetReference(match)) decodeHtmlAssetPath(source) else source
                val assetPath = Uri.decode(unescapeMarkdownAssetPath(assetSource.removePrefix("../")))
                val assetFile = safeOutputFile(bookDir, assetPath)
                val isInsideAssets = assetFile.path == assetRoot.path || assetFile.path.startsWith(assetRoot.path + File.separator)
                require(isInsideAssets) {
                    "asset path is outside assets: $source"
                }
                require(assetFile.exists() && assetFile.isFile) {
                    "asset file is missing: $source"
                }
            }
        }
    }

    private fun assetReferenceFromMatch(match: MatchResult): String? {
        if (match.groupValues[1].isNotBlank()) return match.groupValues[1]
        return match.groupValues.drop(1).firstOrNull { it.isNotBlank() }
    }

    private fun isHtmlAssetReference(match: MatchResult): Boolean {
        return match.groupValues[1].isNotBlank() ||
            match.groupValues[2].isNotBlank() ||
            match.groupValues[3].isNotBlank()
    }

    private fun unescapeMarkdownAssetPath(path: String): String {
        return path
            .replace("\\(", "(")
            .replace("\\)", ")")
    }

    private fun decodeHtmlAssetPath(path: String): String {
        val decodedNamedEntities = HTML_NAMED_ENTITY_PATTERN.replace(path) { match ->
            when (match.groupValues[1].lowercase()) {
                "amp" -> "&"
                "quot" -> "\""
                "apos" -> "'"
                "lt" -> "<"
                "gt" -> ">"
                else -> match.value
            }
        }.replace("&#39;", "'")
        return HTML_NUMERIC_ENTITY_PATTERN.replace(decodedNamedEntities) { match ->
            val codePoint = if (match.groupValues[1].isNotBlank()) {
                match.groupValues[1].toIntOrNull(16)
            } else {
                match.groupValues[2].toIntOrNull(10)
            }
            if (codePoint == null) return@replace match.value
            runCatching {
                Character.toChars(codePoint).concatToString()
            }.getOrDefault(match.value)
        }
    }

    private fun safeOutputFile(targetDir: File, entryName: String): File {
        val root = targetDir.canonicalFile
        val output = File(targetDir, entryName).canonicalFile
        require(output.path == root.path || output.path.startsWith(root.path + File.separator)) {
            "Invalid entry path: $entryName"
        }
        return output
    }

    private fun stagingDir(target: File): File {
        return File(rootDir, ".${target.name}.importing-${System.currentTimeMillis()}")
    }

    private fun targetBackup(target: File): File {
        return File(rootDir, ".${target.name}.backup-${System.currentTimeMillis()}")
    }

    private fun safeBookDirName(name: String): String {
        val cleaned = name.replace(Regex("[^\\p{L}\\p{N}._-]+"), "_").trim('_', '.', ' ')
        return cleaned.ifBlank { "book" }
    }

    fun readManifest(bookDir: File): BookManifest {
        val json = JSONObject(File(bookDir, "book.json").readText())
        val chaptersJson = json.optJSONArray("chapters")
        val chapters = mutableListOf<BookChapter>()
        if (chaptersJson != null) {
            for (index in 0 until chaptersJson.length()) {
                val item = requireNotNull(chaptersJson.optJSONObject(index)) {
                    "chapter entry is invalid: $index"
                }
                chapters.add(
                    BookChapter(
                        id = item.optString("id"),
                        title = item.optString("title"),
                        path = item.optString("path"),
                        order = item.optInt("order"),
                    )
                )
            }
        }
        return BookManifest(
            bookId = json.optString("book_id"),
            title = json.optString("title"),
            formatVersion = json.optString("format_version").takeIf { it.isNotBlank() },
            chapters = chapters,
        )
    }

    fun readManifestOrNull(bookDir: File): BookManifest? {
        return runCatching { readManifest(bookDir) }.getOrNull()
    }

    fun readChapterMarkdown(bookDir: File, chapter: BookChapter): String {
        return safeOutputFile(bookDir, chapter.path).readText()
    }

    fun readChapterMarkdown(bookDir: File, chapterPath: String): String {
        return safeOutputFile(bookDir, chapterPath).readText()
    }

    fun readChapterMarkdownOrNull(bookDir: File, chapterPath: String): String? {
        return runCatching { readChapterMarkdown(bookDir, chapterPath) }.getOrNull()
    }

    fun chapterFileExists(bookDir: File, chapterPath: String): Boolean {
        return runCatching {
            val chapterFile = safeOutputFile(bookDir, chapterPath)
            chapterFile.exists() && chapterFile.isFile
        }.getOrDefault(false)
    }

    fun deleteBook(bookDir: File): Boolean {
        return runCatching {
            val root = rootDir.canonicalFile
            val target = bookDir.canonicalFile
            if (target.path == root.path || !target.path.startsWith(root.path + File.separator)) {
                return false
            }
            val manifest = File(target, "book.json")
            if (!target.isDirectory || !manifest.exists()) {
                return false
            }
            target.exists() && target.deleteRecursively()
        }.getOrDefault(false)
    }

    companion object {
        private val HTML_NAMED_ENTITY_PATTERN = Regex("""&(amp|quot|apos|lt|gt);""", RegexOption.IGNORE_CASE)
        private val HTML_NUMERIC_ENTITY_PATTERN = Regex("""&#(?:x([0-9A-Fa-f]+)|([0-9]+));""")
        private val ASSET_REFERENCE_PATTERN = Regex(
            """(?<![\w:-])src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))|\]\(<(\.\./assets/[^>]+)>(\s+["'][^"']*["'])?\)|\]\((\.\./assets/(?:\\\)|[^)])*?)(\s+["'][^"']*["'])?\)""",
            RegexOption.IGNORE_CASE,
        )
    }
}
