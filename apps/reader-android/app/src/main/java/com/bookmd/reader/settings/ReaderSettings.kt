package com.bookmd.reader.settings

import android.content.Context

data class ReaderSettings(
    val fontSize: Int = 18,
    val lineHeight: Double = 1.75,
    val theme: String = "light",
    val layout: String = "paged",
    val languageMode: String = "zh",
) {
    fun save(context: Context) {
        val normalized = normalized()
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_FONT_SIZE, normalized.fontSize)
            .putString(KEY_LINE_HEIGHT, normalized.lineHeight.toString())
            .putString(KEY_THEME, normalized.theme)
            .putString(KEY_LAYOUT, normalized.layout)
            .putString(KEY_LANGUAGE_MODE, normalized.languageMode)
            .apply()
    }

    fun normalized(): ReaderSettings {
        val fallback = ReaderSettings()
        val safeLineHeight = if (lineHeight.isFinite()) {
            lineHeight.coerceIn(MIN_LINE_HEIGHT, MAX_LINE_HEIGHT)
        } else {
            fallback.lineHeight
        }
        return copy(
            fontSize = fontSize.coerceIn(MIN_FONT_SIZE, MAX_FONT_SIZE),
            lineHeight = safeLineHeight,
            theme = normalizeChoice(theme, ALLOWED_THEMES, ReaderSettings().theme),
            layout = normalizeChoice(layout, ALLOWED_LAYOUTS, ReaderSettings().layout),
            languageMode = normalizeChoice(languageMode, ALLOWED_LANGUAGE_MODES, ReaderSettings().languageMode),
        )
    }

    companion object {
        private const val PREFS_NAME = "bookmd_reader_settings"
        private const val KEY_FONT_SIZE = "font_size"
        private const val KEY_LINE_HEIGHT = "line_height"
        private const val KEY_THEME = "theme"
        private const val KEY_LAYOUT = "layout"
        private const val KEY_LANGUAGE_MODE = "language_mode"
        private const val MIN_FONT_SIZE = 14
        private const val MAX_FONT_SIZE = 28
        private const val MIN_LINE_HEIGHT = 1.3
        private const val MAX_LINE_HEIGHT = 2.4
        private val ALLOWED_THEMES = setOf("light", "dark")
        private val ALLOWED_LAYOUTS = setOf("paged", "scroll")
        private val ALLOWED_LANGUAGE_MODES = setOf("zh", "en", "bilingual")

        fun load(context: Context, defaults: ReaderSettings = ReaderSettings()): ReaderSettings {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return ReaderSettings(
                fontSize = safeInt(prefs, KEY_FONT_SIZE, defaults.fontSize),
                lineHeight = (safeString(prefs, KEY_LINE_HEIGHT, null)?.toDoubleOrNull()
                    ?: defaults.lineHeight),
                theme = safeString(prefs, KEY_THEME, defaults.theme) ?: defaults.theme,
                layout = safeString(prefs, KEY_LAYOUT, defaults.layout) ?: defaults.layout,
                languageMode = safeString(prefs, KEY_LANGUAGE_MODE, defaults.languageMode)
                    ?: defaults.languageMode,
            ).normalized()
        }

        private fun safeInt(
            prefs: android.content.SharedPreferences,
            key: String,
            default: Int,
        ): Int {
            return runCatching { prefs.getInt(key, default) }.getOrDefault(default)
        }

        private fun safeString(
            prefs: android.content.SharedPreferences,
            key: String,
            default: String?,
        ): String? {
            return runCatching { prefs.getString(key, default) }.getOrDefault(default)
        }

        private fun normalizeChoice(value: String, allowed: Set<String>, fallback: String): String {
            return if (value in allowed) value else fallback
        }
    }
}
