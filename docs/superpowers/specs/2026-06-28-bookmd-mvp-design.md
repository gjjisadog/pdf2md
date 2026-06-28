# BookMD MVP Design

## 目标

第一阶段目标是建立一个可运行、可测试、可继续扩展的个人本地 PDF 转 Markdown Book 工程骨架。系统不做 OCR 模型部署，只消费外部 OCR / 文档解析模块已经生成的 `ocr_output/`，并把它转换成 `.bookmd` zip 包。Android 端第一阶段提供能承载 `.bookmd` 阅读能力的工程骨架和渲染资产接口，不追求完整商业级阅读体验。

本阶段完成后，应能用仓库内样例 OCR 输出生成 `.bookmd`，校验其结构完整性，并让 Android 阅读器工程具备打开、解包、读取元数据、加载章节 HTML/Markdown 的基础路径。

## 范围

包含：

- 创建 monorepo 结构：`apps/`、`packages/`、`docs/`、`samples/`、`tests/`。
- 实现 Python CLI 转换器 MVP：读取 `result.json` / `result.md`，生成章节 Markdown、元数据、source map、搜索索引、阅读配置，并打包 `.bookmd`。
- 实现 `.bookmd` 核心库 MVP：构建、校验、读取 zip 内结构。
- 实现 source map 核心逻辑 MVP：从 OCR block 生成可追溯映射。
- 实现 translator-core 的接口、缓存与占位翻译策略；真实 DeepSeek 调用保留接口和配置，但默认不联网调用。
- 实现 markdown-renderer 的移动端 HTML 渲染资产 MVP：CommonMark/GFM、KaTeX 预留、自定义 `formula` / `figure` / `table` / `bilingual` 块样式和脚本接口。
- 创建样例 OCR 输出、占位资产、占位 PDF 说明或文件。
- 编写最小测试，覆盖生成、校验、source_map、搜索索引、错误处理。
- 创建 Android WebView 阅读器骨架：书架、目录、阅读页、设置入口、文件解包和元数据读取的代码边界。

不包含：

- PaddleOCR、PaddleX、PP-StructureV3、CUDA、GPU、OCR 训练或模型部署。
- 上传 PDF 或内容到第三方云端。
- 账号系统、云同步、支付、社交功能。
- Android 端完整分页引擎、完整 UI 精修、PDF 区域截图追溯。
- 第一阶段默认不做真实 DeepSeek API 调用的端到端验证；只保留 provider 接口、配置、缓存和可替换实现。

## 架构

仓库采用 monorepo：

```text
pdf-bookmd-reader/
  README.md
  docs/
  apps/
    converter-desktop/
    reader-android/
  packages/
    bookmd-core/
    markdown-renderer/
    translator-core/
    source-map-core/
  samples/
    ocr_output_sample/
    bookmd_sample/
  tests/
```

Python 侧以包方式组织，优先保证 CLI 可运行和测试可覆盖：

- `apps/converter-desktop`：命令行入口，负责参数解析、配置加载、日志输出、转换流程编排。
- `packages/bookmd-core`：`.bookmd` 目录构建、zip 打包、结构校验、读取 manifest。
- `packages/source-map-core`：OCR block 到 `source_map.json` 的映射生成和查询模型。
- `packages/translator-core`：翻译接口、缓存键、占位翻译、DeepSeek provider 配置。
- `packages/markdown-renderer`：移动端渲染 HTML/CSS/JS 资产，供 Android WebView 加载。

Android 侧使用 Kotlin + WebView。理由是 `.bookmd` 的内容核心是 Markdown/HTML、公式、图片和表格，WebView 能复用前端渲染资产，降低第一版实现成本，并为分页、滚动、图片放大、source map 点击查询留下统一 DOM 接口。

## `.bookmd` 数据格式

`.bookmd` 是 zip 包，MVP 内部结构固定为：

```text
book.json
chapters/
assets/
source/
source_map.json
terms.json
translation.json
reading_config.json
search_index.json
```

`book.json` 记录书籍 ID、标题、作者、语言、版本、创建时间和章节列表。MVP 使用 OCR 标题 block 或文件名推断标题，无法推断时使用 `Untitled Book`。

`source_map.json` 记录 block 到 PDF 页码、bbox、源文本、译文、Markdown 文件路径和 block 类型的关系。所有可追溯内容都保留 `block_id`。

`reading_config.json` 使用默认中文、分页、18px 字号、1.75 行距、浅色主题和段落缩进。

`search_index.json` MVP 使用 JSON 数组索引，按 block 保存章节、标题、block_id、文本片段和语言。第一阶段搜索中文译文；未翻译时索引 OCR 文本。

## 转换流程

CLI 示例：

```bash
python -m converter build \
  --source-pdf "D:/books/test.pdf" \
  --ocr-output "D:/books/ocr_output/test" \
  --output "D:/books/output/test.bookmd" \
  --translate false \
  --target-lang zh \
  --provider noop
```

流程：

1. 校验输入路径：原 PDF、`result.json`、`result.md`。
2. 读取 `result.json`，兼容 `pages[].blocks[]` 和顶层 `blocks[]` 两类常见结构。
3. 规范化 block：补齐 `block_id`、`page`、`bbox`、`type`、`text`、asset 路径。
4. 生成章节：优先按 heading 拆分；没有 heading 时生成单章节。
5. 生成章节 Markdown：每个 block 前写入 HTML 注释保存 `block_id`、页码、bbox。
6. 复制 assets 到 `.bookmd/assets/`，复制原 PDF 到 `.bookmd/source/original.pdf`。
7. 生成 `book.json`、`source_map.json`、`terms.json`、`translation.json`、`reading_config.json`、`search_index.json`。
8. 打包为 `.bookmd` zip。
9. 重新打开 zip 做完整性校验。
10. 输出转换日志。

## Markdown 生成规则

MVP 支持以下 block 类型：

- `heading`：根据 `level` 生成 `#`、`##`、`###`，默认一级标题。
- `paragraph`：生成自然段。
- `formula`：有 `latex` 时生成 `$$...$$`；否则生成 `:::formula` 图片块。
- `figure`：生成 `:::figure` 块。
- `table`：有 `markdown` 时生成 Markdown 表格；否则生成 `:::table` 图片块。
- `caption`：生成普通 caption 段落，并保留类型到 source map。
- `footnote`：能识别时生成 Markdown 脚注，否则作为普通段落并标注类型。

所有 block 都必须尽量保留：

```markdown
<!-- block_id: p001_b003; page: 1; bbox: [72,188,510,246] -->
```

## 翻译设计

第一阶段 `translator-core` 只实现稳定边界，不默认真实联网：

- `Translator` 接口：输入 block 列表，输出按 `block_id` 对齐的翻译结果。
- `NoopTranslator`：返回原文或空译文，用于默认转换和测试。
- `DeepSeekTranslator`：保留配置读取、API key 检查、请求参数结构、重试和超时接口；真实调用可以后续补齐。
- 缓存：按 provider、目标语言、文本 hash 生成缓存键，保存到本地 JSONL 或 JSON 文件。

当用户启用 `--translate true --provider deepseek` 但缺少 `DEEPSEEK_API_KEY` 时，CLI 返回明确错误，不生成半成品文件。

## Android 阅读器设计

第一阶段 Android 工程目标是建立可继续开发的本地阅读器骨架：

- `BookRepository`：导入 `.bookmd`，解压到 App 私有目录，读取 `book.json`。
- `BookShelfActivity`：显示已导入书籍列表的最小页面。
- `TocActivity` 或 Fragment：读取章节列表。
- `ReaderActivity`：WebView 加载本地渲染 HTML，注入章节 Markdown/HTML 和阅读配置。
- `ReaderSettings`：保存字号、行距、主题、布局模式、语言模式。
- `SourceMapRepository`：按 `block_id` 读取 `source_map.json`。

分页第一阶段采用 WebView CSS columns / JS 接口预留。若实现完整分页风险过高，先提供稳定滚动和仿分页结构，但默认配置仍写为 `paged`，代码中保留分页适配层。

## 错误处理

转换器必须把以下情况转换为明确错误消息和非 0 退出码：

- `result.json` 不存在或 JSON 无法解析。
- `result.md` 不存在。
- source PDF 不存在。
- OCR block 结构为空。
- asset 路径缺失时保留警告，并继续生成引用可诊断的 Markdown。
- `.bookmd` 打包失败。
- `.bookmd` 校验失败。
- 启用 DeepSeek 但缺少 API key。

Android 侧必须把解压失败、manifest 缺失、章节文件缺失、WebView 加载失败转化为用户可理解的错误状态，而不是直接崩溃。

## 测试与验证

第一阶段验证命令：

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
```

测试覆盖：

- 样例 OCR 输出能生成 `.bookmd`。
- `.bookmd` 包含必需文件。
- `book.json` 章节结构有效。
- `source_map.json` 能按 block_id 追溯页码、bbox、原文。
- `search_index.json` 包含可搜索中文内容。
- 缺少 `result.json`、`result.md`、source PDF 时返回明确错误。
- 启用 DeepSeek 且缺少 API key 时返回明确错误。

Android 第一阶段验证：

- Gradle 工程能同步或至少具备标准项目结构。
- 阅读器代码边界明确，后续可接入真实 `.bookmd` 文件导入。
- WebView 资产能渲染自定义 `figure`、`formula`、`table` 块的静态 HTML。

## 里程碑

1. 工程骨架和文档。
2. Python 数据模型、异常和 `.bookmd` 校验测试。
3. OCR block 规范化、章节生成和 Markdown 生成。
4. CLI build / validate 闭环。
5. 样例数据和端到端测试。
6. Android 阅读器骨架与 WebView 渲染资产。

## 设计自检

- 无真实 OCR / Paddle 相关工作。
- 无云上传、账号、同步和商业化功能。
- MVP 目标可通过本地样例和自动化测试验证。
- 翻译保留接口但默认不联网，避免第一阶段被外部 API 阻塞。
- Android 第一阶段明确为骨架和可扩展边界，避免一次性实现完整阅读器造成范围失控。
