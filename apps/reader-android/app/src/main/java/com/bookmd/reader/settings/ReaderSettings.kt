package com.bookmd.reader.settings

data class ReaderSettings(
    val fontSize: Int = 18,
    val lineHeight: Double = 1.75,
    val theme: String = "light",
    val layout: String = "paged",
    val languageMode: String = "zh",
)
