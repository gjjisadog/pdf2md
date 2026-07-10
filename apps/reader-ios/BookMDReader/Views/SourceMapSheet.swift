import SwiftUI
import BookMDReaderCore

struct SourceMapSheet: View {
    @Environment(\.dismiss) private var dismiss

    let block: SourceMapBlock
    let onOpenPDF: ((Int) -> Void)?

    var body: some View {
        NavigationStack {
            List {
                Section("定位") {
                    HStack {
                        Text("页码")
                        Spacer()
                        Text("\(block.sourcePage)")
                            .foregroundStyle(.secondary)
                            .accessibilityIdentifier("sourceMap.page.\(block.sourcePage)")
                    }
                    HStack {
                        Text("类型")
                        Spacer()
                        Text(block.type)
                            .foregroundStyle(.secondary)
                            .accessibilityIdentifier("sourceMap.type.\(block.type)")
                    }
                    let bboxText = block.bbox.map { clean($0) }.joined(separator: ", ")
                    HStack {
                        Text("BBox")
                        Spacer()
                        Text(bboxText)
                            .foregroundStyle(.secondary)
                            .accessibilityIdentifier("sourceMap.bbox.\(bboxText)")
                    }
                    if let onOpenPDF {
                        Button {
                            onOpenPDF(block.sourcePage)
                            dismiss()
                        } label: {
                            Label("查看原 PDF 页", systemImage: "doc.richtext")
                        }
                    }
                }

                Section("原文") {
                    Text(block.sourceText.isEmpty ? "No source text available." : block.sourceText)
                        .textSelection(.enabled)
                }

                if let translated = block.translatedText, !translated.isEmpty {
                    Section("译文") {
                        Text(translated)
                            .textSelection(.enabled)
                    }
                }
            }
            .accessibilityIdentifier("sourceMap.sheet")
            .navigationTitle(block.blockId)
        }
        .presentationDetents([.medium, .large])
    }

    private func clean(_ value: Double) -> String {
        value.rounded() == value ? "\(Int(value))" : "\(value)"
    }
}
