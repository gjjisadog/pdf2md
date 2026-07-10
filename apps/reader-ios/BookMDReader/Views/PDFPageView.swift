import PDFKit
import SwiftUI

struct PDFPageView: UIViewRepresentable {
    let pdfURL: URL
    let pageNumber: Int

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        return view
    }

    func updateUIView(_ view: PDFView, context: Context) {
        if view.document?.documentURL != pdfURL {
            view.document = PDFDocument(url: pdfURL)
        }
        guard let page = view.document?.page(at: max(0, pageNumber - 1)) else { return }
        view.go(to: page)
    }
}

struct PDFPageSheet: View {
    @Environment(\.dismiss) private var dismiss

    let pdfURL: URL
    let pageNumber: Int

    var body: some View {
        NavigationStack {
            PDFPageView(pdfURL: pdfURL, pageNumber: pageNumber)
                .navigationTitle("PDF 第 \(pageNumber) 页")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("完成") {
                            dismiss()
                        }
                        .accessibilityIdentifier("pdf.done")
                    }
                }
        }
    }
}
