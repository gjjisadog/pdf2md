import SwiftUI

struct ReaderSettingsSheet: View {
    @Environment(\.dismiss) private var dismiss

    @Binding var settings: ReaderDisplaySettings

    var body: some View {
        NavigationStack {
            Form {
                Section("文字") {
                    Stepper("字号 \(settings.fontSize)", value: $settings.fontSize, in: 14...28)
                        .accessibilityIdentifier("reader.settings.fontSize")
                    HStack {
                        Text("行高")
                        Slider(value: $settings.lineHeight, in: 1.3...2.2, step: 0.05)
                            .accessibilityIdentifier("reader.settings.lineHeight")
                        Text(settings.lineHeight, format: .number.precision(.fractionLength(2)))
                            .monospacedDigit()
                            .foregroundStyle(.secondary)
                    }
                }

                Section("显示") {
                    Picker("主题", selection: $settings.theme) {
                        Text("浅色").tag("light")
                        Text("深色").tag("dark")
                    }
                    .accessibilityIdentifier("reader.settings.theme")
                    Picker("布局", selection: $settings.layout) {
                        Text("连续").tag("scroll")
                        Text("分页").tag("paged")
                    }
                    .accessibilityIdentifier("reader.settings.layout")
                    Picker("语言", selection: $settings.languageMode) {
                        Text("中文").tag("zh")
                        Text("英文").tag("en")
                        Text("双语").tag("bilingual")
                    }
                    .accessibilityIdentifier("reader.settings.language")
                }
            }
            .accessibilityIdentifier("reader.settings.form")
            .navigationTitle("阅读设置")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") {
                        dismiss()
                    }
                    .accessibilityIdentifier("reader.settings.done")
                }
            }
        }
        .presentationDetents([.medium])
    }
}
