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
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_FONT_SIZE, fontSize)
            .putString(KEY_LINE_HEIGHT, lineHeight.toString())
            .putString(KEY_THEME, theme)
            .putString(KEY_LAYOUT, layout)
            .putString(KEY_LANGUAGE_MODE, languageMode)
            .apply()
    }

    companion object {
        private const val PREFS_NAME = "bookmd_reader_settings"
        private const val KEY_FONT_SIZE = "font_size"
        private const val KEY_LINE_HEIGHT = "line_height"
        private const val KEY_THEME = "theme"
        private const val KEY_LAYOUT = "layout"
        private const val KEY_LANGUAGE_MODE = "language_mode"

        fun load(context: Context, defaults: ReaderSettings = ReaderSettings()): ReaderSettings {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return ReaderSettings(
                fontSize = prefs.getInt(KEY_FONT_SIZE, defaults.fontSize),
                lineHeight = (prefs.getString(KEY_LINE_HEIGHT, null)?.toDoubleOrNull()
                    ?: defaults.lineHeight),
                theme = prefs.getString(KEY_THEME, defaults.theme) ?: defaults.theme,
                layout = prefs.getString(KEY_LAYOUT, defaults.layout) ?: defaults.layout,
                languageMode = prefs.getString(KEY_LANGUAGE_MODE, defaults.languageMode)
                    ?: defaults.languageMode,
            )
        }
    }
}
