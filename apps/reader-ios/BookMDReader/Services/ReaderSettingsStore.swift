import Foundation
import BookMDReaderCore

final class ReaderSettingsStore {
    private let defaults: UserDefaults
    private let keyPrefix: String

    init(bookId: String, defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.keyPrefix = "reader.\(bookId)."
    }

    func load(defaultConfig: ReadingConfig) -> ReaderDisplaySettings {
        var settings = ReaderDisplaySettings(config: defaultConfig)
        if defaults.object(forKey: key("fontSize")) != nil {
            settings.fontSize = defaults.integer(forKey: key("fontSize"))
        }
        if defaults.object(forKey: key("lineHeight")) != nil {
            settings.lineHeight = defaults.double(forKey: key("lineHeight"))
        }
        settings.theme = defaults.string(forKey: key("theme")) ?? settings.theme
        settings.layout = defaults.string(forKey: key("layout")) ?? settings.layout
        settings.languageMode = defaults.string(forKey: key("languageMode")) ?? settings.languageMode
        return settings.normalized()
    }

    func save(_ settings: ReaderDisplaySettings) {
        let normalized = settings.normalized()
        defaults.set(normalized.fontSize, forKey: key("fontSize"))
        defaults.set(normalized.lineHeight, forKey: key("lineHeight"))
        defaults.set(normalized.theme, forKey: key("theme"))
        defaults.set(normalized.layout, forKey: key("layout"))
        defaults.set(normalized.languageMode, forKey: key("languageMode"))
    }

    private func key(_ name: String) -> String {
        keyPrefix + name
    }
}
