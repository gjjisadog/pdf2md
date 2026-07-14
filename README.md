# PDF BookMD Reader

个人本地使用的专业 PDF 转 Markdown Book 工程。

第一版只消费外部 OCR / 文档解析模块已经生成的 `ocr_output/`，不部署 PaddleOCR、PaddleX、PP-StructureV3，也不训练模型。

## MVP 目标

- 从样例 `ocr_output` 生成 `.bookmd`。
- 校验 `.bookmd` 内部结构。
- 保留 Markdown、assets、source map、搜索索引和原 PDF。
- 提供 Android WebView 阅读器工程。
- 提供 iPadOS SwiftUI + WKWebView 阅读器工程。
- 支持可缓存、可测试的 DeepSeek/Noop 翻译边界与双语阅读输出。

## 快速验证

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd --strict
```

干净环境安装与构建：

```bash
python -m pip install -e '.[dev]'
python -m build --wheel
bookmd --help
```

安装后的 `bookmd` 命令与 `python -m converter` 使用同一套 CLI；CI 会在全新虚拟环境中安装 wheel 后执行样例构建和严格校验。

发布前完整验证：

```bash
python scripts/verify_release.py
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

第四阶段继续强化 renderer 与阅读体验：

- Android WebView 使用 `packages/markdown_renderer/renderer` 同源资产。
- renderer 支持代码块、Markdown 表格、脚注、引用链接、锚点和语言模式。
- Android 增加设置页、图片/表格全屏查看和章节阅读进度保存/恢复。

第五阶段完成转换器和翻译链路加固：

- `translator_core` 提供 mockable DeepSeek client、JSON 响应校验、JSONL translation cache。
- 转换器生成 `terms.json`、更完整的 `translation.json`、翻译后的 source map/search index。
- 支持 `translation.bilingual: true` 的双语章节 Markdown。

Phase 6 完成个人 MVP 发布验收闭环：

- `scripts/verify_release.py` 串起 Python tests、样例 `.bookmd` 构建/校验、renderer parity，检测到 Android SDK 时构建 debug APK。
- 文档覆盖 Windows converter、DeepSeek setup、Android reader、troubleshooting、release checklist 和 final acceptance。

Phase 7 增加通用 HTTP OCR API 接入：

- 本项目仍不部署 OCR 模型，不安装 PaddleOCR/PaddleX/PP-StructureV3。
- 新增 `ocr_client`，通过 `OCR_API_URL` / `OCR_API_KEY` 调用外部 HTTP OCR 服务。
- `python -m converter ocr` 可把 PDF 转成标准 `ocr_output/`。
- `python -m converter build-from-pdf` 可串起 OCR API 和 `.bookmd` 构建。

Phase 8 增加 iPadOS BookMD 阅读器：

- `apps/reader-ios/` 提供 iPad mini 优先的 SwiftUI + WKWebView 阅读器。
- 支持 Files 导入 `.bookmd`、书架、目录、阅读、搜索跳转、source map、阅读进度、术语表、PDF 页回看和阅读设置。
- `python3 apps/reader-ios/scripts/verify_ios_static.py` 验证 iOS 工程结构、renderer parity 和真实 `.bookmd` 样本基准。
- `python3 apps/reader-ios/scripts/verify_ios_release.py` 是 iOS release gate；当前本机 Xcode 框架错配时可用 `--allow-xcode-blocked` 保留静态验收结果。

## 目录

- `apps/converter_desktop/`: Windows/desktop 转换器 CLI。
- `apps/reader-android/`: Android WebView 阅读器骨架。
- `apps/reader-ios/`: iPadOS SwiftUI + WKWebView 阅读器工程。
- `packages/bookmd_core/`: `.bookmd` 打包与校验。
- `packages/source_map_core/`: OCR block 规范化与 source map。
- `packages/translator_core/`: 翻译接口、DeepSeek client、缓存和术语抽取。
- `packages/ocr_client/`: 通用 HTTP OCR API client 与 `ocr_output` 写入。
- `packages/markdown_renderer/`: 移动端渲染资产。
- `samples/ocr_output_sample/`: 不依赖真实 OCR 的假数据样例。
- `docs/ci_runner_setup.md`: Gitea Actions runner 标签、注册和 Windows CI 验收说明。

BookMD 1.0 包使用 `format_version: "1.0"`。`bookmd validate` 与 `bookmd quality-report` 默认执行严格 schema、ZIP 路径/重复项/大小安全、章节与 source map/search/translation 引用以及 Markdown 图片资产校验；需要旧工具的结构兼容检查时可显式使用 `--compat`。缺少 `format_version` 的 0.1 包仍可读取，但会给出迁移 warning。PDF 封面与 figure/formula/table fallback 默认由 PDFium + Pillow 生成，不依赖 Swift、`pdftoppm` 或 `sips`。

Android debug APK 构建后位于：

```text
apps/reader-android/app/build/outputs/apk/debug/app-debug.apk
```

iPadOS 阅读器工程位于：

```text
apps/reader-ios/BookMDReader.xcodeproj
```
