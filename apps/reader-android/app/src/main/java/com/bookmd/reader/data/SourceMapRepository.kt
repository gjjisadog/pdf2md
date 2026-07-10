package com.bookmd.reader.data

import java.io.File
import org.json.JSONArray
import org.json.JSONObject

data class SourceMapBlock(
    val blockId: String,
    val sourcePage: Int,
    val bbox: String,
    val sourceText: String,
    val type: String,
)

class SourceMapRepository(private val bookDir: File) {
    fun readSourceMap(): String {
        return File(bookDir, "source_map.json").readText()
    }

    fun findBlockOrNull(blockId: String): SourceMapBlock? {
        return runCatching { findBlock(blockId) }.getOrNull()
    }

    fun findBlock(blockId: String): SourceMapBlock? {
        val requestedBlockId = blockId.trim()
        if (requestedBlockId.isBlank()) return null
        val root = JSONObject(readSourceMap())
        val blocks = root.optJSONArray("blocks") ?: return null
        for (index in 0 until blocks.length()) {
            val item = blocks.optJSONObject(index) ?: continue
            if (item.optString("block_id") == requestedBlockId) {
                val sourcePage = item.optInt("source_page")
                if (sourcePage < 1) continue
                val bbox = item.optJSONArray("bbox") ?: continue
                if (bbox.length() != 4) continue
                if (!bboxIsValid(bbox)) continue
                return SourceMapBlock(
                    blockId = item.optString("block_id"),
                    sourcePage = sourcePage,
                    bbox = bbox.toString(),
                    sourceText = item.optString("source_text"),
                    type = item.optString("type"),
                )
            }
        }
        return null
    }

    private fun bboxIsValid(bbox: JSONArray): Boolean {
        for (index in 0 until bbox.length()) {
            val value = bbox.optDouble(index)
            if (!value.isFinite()) return false
        }
        val left = bbox.optDouble(0)
        val top = bbox.optDouble(1)
        val right = bbox.optDouble(2)
        val bottom = bbox.optDouble(3)
        return right > left && bottom > top
    }
}
