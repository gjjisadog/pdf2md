package com.bookmd.reader.data

import java.io.File
import org.json.JSONObject

data class SearchResult(
    val blockId: String,
    val chapterId: String,
    val chapterPath: String,
    val chapterTitle: String,
    val text: String,
    val snippet: String,
    val matchStart: Int,
    val matchEnd: Int,
)

class SearchRepository(private val bookDir: File) {
    fun searchOrEmpty(query: String): List<SearchResult> {
        return runCatching { search(query) }.getOrElse { emptyList() }
    }

    fun search(query: String): List<SearchResult> {
        val normalizedQuery = query.trim()
        if (normalizedQuery.isBlank()) return emptyList()
        if (normalizedQuery.length > MAX_SEARCH_QUERY_LENGTH) return emptyList()
        val indexFile = File(bookDir, "search_index.json")
        if (!indexFile.exists()) return emptyList()
        val root = JSONObject(indexFile.readText())
        val items = root.optJSONArray("items") ?: return emptyList()
        val results = mutableListOf<SearchResult>()
        for (index in 0 until items.length()) {
            val item = items.optJSONObject(index) ?: continue
            val blockId = item.optString("block_id")
            if (blockId.isBlank()) continue
            val chapterPath = item.optString("chapter_path")
            if (chapterPath.isBlank()) continue
            if (!chapterFileExists(chapterPath)) continue
            val text = item.optString("text")
            val matchIndex = text.indexOf(normalizedQuery, ignoreCase = true)
            if (matchIndex >= 0) {
                val snippet = buildSnippet(text, matchIndex, normalizedQuery.length)
                results.add(
                    SearchResult(
                        blockId = blockId,
                        chapterId = item.optString("chapter_id"),
                        chapterPath = chapterPath,
                        chapterTitle = displayChapterTitle(item, chapterPath),
                        text = text,
                        snippet = snippet.text,
                        matchStart = snippet.matchStart,
                        matchEnd = snippet.matchEnd,
                    )
                )
                if (results.size >= MAX_SEARCH_RESULTS) break
            }
        }
        return results
    }

    private fun chapterFileExists(chapterPath: String): Boolean {
        return runCatching {
            val root = bookDir.canonicalFile
            val chapterFile = File(bookDir, chapterPath).canonicalFile
            val isInsideBook = chapterFile.path == root.path || chapterFile.path.startsWith(root.path + File.separator)
            isInsideBook && chapterFile.exists() && chapterFile.isFile
        }.getOrDefault(false)
    }

    private fun displayChapterTitle(item: JSONObject, chapterPath: String): String {
        return item.optString("chapter_title").ifBlank {
            chapterPath.substringAfterLast('/').ifBlank {
                item.optString("chapter_id").ifBlank { "Untitled chapter" }
            }
        }
    }

    private fun buildSnippet(text: String, matchStart: Int, queryLength: Int): SearchSnippet {
        val context = 48
        val start = (matchStart - context).coerceAtLeast(0)
        val end = (matchStart + queryLength + context).coerceAtMost(text.length)
        val prefix = if (start > 0) "..." else ""
        val suffix = if (end < text.length) "..." else ""
        val snippetText = prefix + text.substring(start, end) + suffix
        val adjustedStart = prefix.length + matchStart - start
        return SearchSnippet(
            text = snippetText,
            matchStart = adjustedStart,
            matchEnd = adjustedStart + queryLength,
        )
    }

    private data class SearchSnippet(
        val text: String,
        val matchStart: Int,
        val matchEnd: Int,
    )

    companion object {
        const val MAX_SEARCH_RESULTS = 200
        const val MAX_SEARCH_QUERY_LENGTH = 128
    }
}
