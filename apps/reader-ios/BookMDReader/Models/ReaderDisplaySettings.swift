import Foundation
import BookMDReaderCore

struct ReaderDisplaySettings: Equatable {
    var fontSize: Int
    var lineHeight: Double
    var theme: String
    var layout: String
    var languageMode: String

    init(config: ReadingConfig) {
        self.fontSize = config.fontSize
        self.lineHeight = config.lineHeight
        self.theme = config.theme
        self.layout = config.layout
        self.languageMode = config.defaultMode
    }

    func normalized() -> ReaderDisplaySettings {
        let validThemes = Set(["light", "dark"])
        let validLayouts = Set(["scroll", "paged"])
        let validLanguageModes = Set(["zh", "en", "bilingual"])

        return ReaderDisplaySettings(
            fontSize: min(max(fontSize, 14), 28),
            lineHeight: min(max(lineHeight, 1.3), 2.2),
            theme: validThemes.contains(theme) ? theme : "light",
            layout: validLayouts.contains(layout) ? layout : "paged",
            languageMode: validLanguageModes.contains(languageMode) ? languageMode : "zh"
        )
    }

    func readingConfig() -> ReadingConfig {
        let settings = normalized()
        return ReadingConfig(
            defaultMode: settings.languageMode,
            layout: settings.layout,
            fontSize: settings.fontSize,
            lineHeight: settings.lineHeight,
            theme: settings.theme,
            paragraphIndent: true
        )
    }

    private init(fontSize: Int, lineHeight: Double, theme: String, layout: String, languageMode: String) {
        self.fontSize = fontSize
        self.lineHeight = lineHeight
        self.theme = theme
        self.layout = layout
        self.languageMode = languageMode
    }
}
