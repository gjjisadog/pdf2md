# PDF BookMD Reader

个人本地使用的专业 PDF 转 Markdown Book 工程。

第一版只消费外部 OCR / 文档解析模块已经生成的 `ocr_output/`，不部署 PaddleOCR、PaddleX、PP-StructureV3，也不训练模型。

## MVP 目标

- 从样例 `ocr_output` 生成 `.bookmd`。
- 校验 `.bookmd` 内部结构。
- 保留 Markdown、assets、source map、搜索索引和原 PDF。
- 提供 Android WebView 阅读器工程骨架。

## 快速验证

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
```

## 目录

- `apps/converter_desktop/`: Windows/desktop 转换器 CLI。
- `apps/reader-android/`: Android WebView 阅读器骨架。
- `packages/bookmd_core/`: `.bookmd` 打包与校验。
- `packages/source_map_core/`: OCR block 规范化与 source map。
- `packages/translator_core/`: 翻译接口与 DeepSeek 配置守卫。
- `packages/markdown_renderer/`: 移动端渲染资产。
- `samples/ocr_output_sample/`: 不依赖真实 OCR 的假数据样例。
