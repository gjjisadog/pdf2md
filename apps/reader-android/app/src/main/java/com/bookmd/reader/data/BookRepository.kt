package com.bookmd.reader.data

import java.io.File
import java.util.zip.ZipFile
import org.json.JSONObject

class BookRepository(private val rootDir: File) {
    fun listBooks(): List<File> {
        return rootDir.listFiles()
            ?.filter { File(it, "book.json").exists() }
            ?.sortedBy { it.name.lowercase() }
            ?: emptyList()
    }

    fun importBook(bookmd: File): File {
        val target = File(rootDir, bookmd.nameWithoutExtension)
        target.mkdirs()
        ZipFile(bookmd).use { zip ->
            zip.entries().asSequence().forEach { entry ->
                val output = File(target, entry.name)
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
        require(File(target, "book.json").exists()) { "book.json is missing" }
        return target
    }

    fun readManifest(bookDir: File): BookManifest {
        val json = JSONObject(File(bookDir, "book.json").readText())
        val chaptersJson = json.optJSONArray("chapters")
        val chapters = mutableListOf<BookChapter>()
        if (chaptersJson != null) {
            for (index in 0 until chaptersJson.length()) {
                val item = chaptersJson.getJSONObject(index)
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
            chapters = chapters,
        )
    }

    fun readChapterMarkdown(bookDir: File, chapter: BookChapter): String {
        return File(bookDir, chapter.path).readText()
    }

    fun readChapterMarkdown(bookDir: File, chapterPath: String): String {
        return File(bookDir, chapterPath).readText()
    }
}
