package com.bookmd.reader

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bookmd.reader.settings.ReaderSettings

class SettingsActivity : Activity() {
    private var settings = ReaderSettings()
    private lateinit var summary: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = ReaderSettings.load(this)
        summary = TextView(this).apply { textSize = 18f }
        setContentView(
            ScrollView(this).apply {
                addView(LinearLayout(this@SettingsActivity).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(32, 32, 32, 32)
                    addView(summary)
                    addView(Button(this@SettingsActivity).apply {
                        text = "Font Size"
                        setOnClickListener {
                            settings = settings.copy(fontSize = nextFontSize(settings.fontSize))
                            saveAndRender()
                        }
                    })
                    addView(Button(this@SettingsActivity).apply {
                        text = "Line Height"
                        setOnClickListener {
                            settings = settings.copy(lineHeight = nextLineHeight(settings.lineHeight))
                            saveAndRender()
                        }
                    })
                    addView(Button(this@SettingsActivity).apply {
                        text = "Theme"
                        setOnClickListener {
                            settings = settings.copy(theme = if (settings.theme == "dark") "light" else "dark")
                            saveAndRender()
                        }
                    })
                    addView(Button(this@SettingsActivity).apply {
                        text = "Layout"
                        setOnClickListener {
                            settings = settings.copy(layout = if (settings.layout == "scroll") "paged" else "scroll")
                            saveAndRender()
                        }
                    })
                    addView(Button(this@SettingsActivity).apply {
                        text = "Language Mode"
                        setOnClickListener {
                            settings = settings.copy(languageMode = nextLanguageMode(settings.languageMode))
                            saveAndRender()
                        }
                    })
                    addView(Button(this@SettingsActivity).apply {
                        text = "Reset Defaults"
                        setOnClickListener {
                            confirmResetDefaults()
                        }
                    })
                })
            }
        )
        saveAndRender()
    }

    private fun confirmResetDefaults() {
        AlertDialog.Builder(this)
            .setTitle("Reset defaults?")
            .setMessage("Restore readable default settings?")
            .setPositiveButton("Reset") { _, _ ->
                settings = ReaderSettings()
                saveAndRender()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun saveAndRender() {
        settings.save(this)
        summary.text = "Font ${settings.fontSize}\nLine ${settings.lineHeight}\nTheme ${settings.theme}\nLayout ${settings.layout}\nMode ${settings.languageMode}"
    }

    private fun nextFontSize(current: Int): Int = when (current) {
        16 -> 18
        18 -> 20
        20 -> 22
        else -> 16
    }

    private fun nextLineHeight(current: Double): Double = when {
        current < 1.7 -> 1.75
        current < 1.9 -> 2.0
        else -> 1.5
    }

    private fun nextLanguageMode(current: String): String = when (current) {
        "zh" -> "en"
        "en" -> "bilingual"
        else -> "zh"
    }
}
