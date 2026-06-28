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

## 当前阶段

第二阶段已经把第一阶段骨架推进到本地阅读闭环雏形：

- 转换器支持 `--config config.yaml`。
- `.bookmd` 包含章节、assets、source map、搜索索引和阅读配置。
- renderer 支持 Markdown/custom block、搜索高亮、block 跳转和 WebView 回调。
- Android 工程包含导入、书架、目录、阅读、搜索、进度和 source map 弹窗边界。

第三阶段继续推进到 Android 可构建阅读 MVP：

- Android 工程带 Gradle wrapper。
- `assembleDebug` 已验证通过。
- App 具备导入 `.bookmd`、书架、目录、阅读、搜索跳转、source map 弹窗主链路代码。

## 目录

- `apps/converter_desktop/`: Windows/desktop 转换器 CLI。
- `apps/reader-android/`: Android WebView 阅读器骨架。
- `packages/bookmd_core/`: `.bookmd` 打包与校验。
- `packages/source_map_core/`: OCR block 规范化与 source map。
- `packages/translator_core/`: 翻译接口与 DeepSeek 配置守卫。
- `packages/markdown_renderer/`: 移动端渲染资产。
- `samples/ocr_output_sample/`: 不依赖真实 OCR 的假数据样例。
