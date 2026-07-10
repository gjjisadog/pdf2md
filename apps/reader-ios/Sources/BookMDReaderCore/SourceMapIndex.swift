import Foundation

public struct SourceMapIndex: Sendable {
    private let blocksById: [String: SourceMapBlock]

    public init(blocks: [SourceMapBlock]) {
        var index: [String: SourceMapBlock] = [:]
        for block in blocks {
            if index[block.blockId] == nil {
                index[block.blockId] = block
            }
        }
        self.blocksById = index
    }

    public func block(for blockId: String) -> SourceMapBlock? {
        blocksById[blockId]
    }
}
