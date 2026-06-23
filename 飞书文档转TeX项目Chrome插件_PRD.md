# PRD：飞书文档转本地 TeX 项目 Chrome 插件

## 1. 产品目标

做一个 Chrome 插件，将当前打开的飞书文档一键转换为本地可编译的 LaTeX/TeX 项目，尽可能保持原文档的结构、样式和排版效果。

核心目标不是“导出纯文本”，而是生成一个可维护、可继续编辑、可版本管理的本地 TeX 项目。

## 2. 背景与问题

飞书文档适合协作写作，但不适合论文、书籍、技术报告等需要精确排版、引用管理、版本控制和本地编译的场景。用户通常需要手动复制内容、下载图片、重建表格、调整公式和标题样式，成本很高且容易出错。

当前痛点：

- 飞书文档到 LaTeX 缺少稳定的一键转换工具。
- 图片、表格、公式、代码块、引用、脚注等元素迁移成本高。
- 手工转换后样式不一致，后续维护困难。
- 多人协作阶段在飞书，定稿阶段在 TeX，链路割裂。

## 3. 目标用户

- 写论文、毕业设计、学术报告的学生和研究人员。
- 用飞书写技术文档，但最终需要 LaTeX/PDF 交付的工程师。
- 需要将团队文档归档到 Git/本地 TeX 项目的知识管理用户。
- 有固定 LaTeX 模板的团队，例如实验室、课程、期刊投稿、技术白皮书团队。

## 4. 使用场景

1. 用户在 Chrome 中打开一篇飞书文档。
2. 点击插件按钮。
3. 插件识别当前文档标题、正文结构、图片、表格、公式等内容。
4. 用户选择导出方式：
   - 下载为 `.zip` 项目包。
   - 选择本地目录后直接写入项目文件。
5. 用户在本地运行 `latexmk` / TeX Live / Overleaf 上传后可直接编译。
6. 用户可继续在本地修改 `.tex` 文件、图片和样式文件。

## 5. 产品范围

MVP 目标：支持常见飞书文档到完整 TeX 项目导出，保证基础结构和主要样式可用。

### P0 功能

- 识别当前飞书文档。
- 获取文档标题、正文块、层级结构。
- 转换标题、段落、粗体、斜体、删除线、下划线、超链接。
- 转换有序列表、无序列表、任务列表。
- 转换图片并保存到 `assets/images/`。
- 转换代码块，保留语言标识。
- 转换公式为 LaTeX 数学环境。
- 转换普通表格。
- 生成完整 TeX 项目结构。
- 支持导出 ZIP。
- 提供转换日志和错误报告。

### P1 功能

- 支持脚注、引用、目录、分栏、callout、高亮块。
- 支持复杂表格，包括合并单元格、列宽、文本对齐。
- 支持飞书附件下载并归档。
- 支持用户选择 TeX 模板。
- 支持增量更新，避免覆盖用户已修改的 TeX 文件。
- 支持本地直接写入目录。

### P2 功能

- 支持自定义样式映射。
- 支持多人团队模板库。
- 支持导出到 Git 仓库。
- 支持自动编译并预览 PDF。
- 支持与 Overleaf 项目同步。

## 6. 非目标

MVP 不做：

- 不承诺 100% 复刻飞书在线渲染效果。
- 不支持所有飞书复杂嵌入对象，例如多维表格、思维导图、互动卡片、第三方插件块。
- 不做完整 LaTeX 编辑器。
- 不内置 TeX 编译环境。
- 不绕过飞书权限系统，只转换当前用户有权限访问的文档。

## 7. 核心用户流程

### 流程 A：快速导出 ZIP

1. 用户打开飞书文档。
2. 点击 Chrome 插件图标。
3. 插件显示文档标题和检测结果。
4. 用户点击“导出 TeX 项目”。
5. 插件生成项目 ZIP。
6. Chrome 下载 ZIP 文件。

### 流程 B：导出到本地文件夹

1. 用户点击“选择本地目录”。
2. 浏览器弹出目录选择授权。
3. 插件写入项目文件。
4. 显示导出完成、文件数量、警告数量。

说明：Chrome 插件不能无感写入任意本地目录。可用方案是下载 ZIP，或通过 File System Access API 让用户授权目录。若后续需要自动编译、Git 提交、写入任意路径，可增加 Native Messaging 本地助手。

参考：

- Chrome File System Access API: <https://developer.chrome.com/docs/capabilities/web-apis/file-system-access>
- Chrome downloads API: <https://developer.chrome.com/docs/extensions/reference/api/downloads>
- Chrome Native Messaging: <https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging>

## 8. 输出项目结构

```text
document-title/
  main.tex
  latexmkrc
  README.md
  styles/
    feishu.sty
  sections/
    01-introduction.tex
    02-background.tex
  assets/
    images/
      image-001.png
      image-002.jpg
    attachments/
  tables/
    table-001.tex
  refs/
    references.bib
  metadata.json
  conversion-report.json
```

`main.tex` 负责全局结构：

```tex
\documentclass[UTF8]{ctexart}
\usepackage{styles/feishu}

\title{飞书文档标题}
\author{}
\date{\today}

\begin{document}
\maketitle
\tableofcontents

\input{sections/01-introduction}
\input{sections/02-background}

\end{document}
```

## 9. 格式映射规则

### 基础文本

| 飞书元素 | TeX 输出 |
|---|---|
| 一级标题 | `\section{}` |
| 二级标题 | `\subsection{}` |
| 三级标题 | `\subsubsection{}` |
| 普通段落 | 普通 TeX 段落 |
| 粗体 | `\textbf{}` |
| 斜体 | `\textit{}` |
| 行内代码 | `\texttt{}` |
| 超链接 | `\href{}{}` |
| 删除线 | `\sout{}` |
| 高亮 | 自定义 `\highlight{}` |

### 列表

| 飞书元素 | TeX 输出 |
|---|---|
| 无序列表 | `itemize` |
| 有序列表 | `enumerate` |
| 任务列表 | 自定义 checkbox 列表 |
| 嵌套列表 | 嵌套 `itemize/enumerate` |

### 复杂内容

| 飞书元素 | TeX 输出 |
|---|---|
| 图片 | `figure` + `\includegraphics` |
| 表格 | `tabularx` / `longtable` |
| 代码块 | `minted` 或 `listings` |
| 块公式 | `equation` / `align` |
| 行内公式 | `$...$` |
| 引用块 | `quote` 或自定义环境 |
| callout | 自定义 `feishucallout` 环境 |
| 分割线 | `\hrulefill` 或自定义命令 |

## 10. 保真度要求

MVP 验收标准：

- 文本内容完整率 >= 99%。
- 标题层级准确率 >= 98%。
- 图片导出成功率 >= 95%，失败项必须出现在报告中。
- 基础表格转换成功率 >= 90%。
- 公式可编译率 >= 95%。
- 生成项目可直接通过 XeLaTeX 或 LuaLaTeX 编译。
- 不可还原元素必须以 TeX 注释形式保留占位，例如：

```tex
% TODO: Unsupported Feishu block: mindmap
```

## 11. 插件功能模块

1. 文档识别模块  
   判断当前页面是否为飞书文档，提取 document token、标题、权限状态。

2. 授权模块  
   处理飞书登录态、API 授权或当前页面读取权限。

3. 内容获取模块  
   优先通过飞书开放接口获取结构化文档数据；必要时用 content script 辅助读取页面中可见样式。

4. 中间 AST 模块  
   将飞书 block 转换为统一的内部文档模型，避免直接从飞书结构硬转 TeX。

5. TeX 转换模块  
   将 AST 转为 `.tex`、`.sty`、图片、表格、元数据等文件。

6. 资产下载模块  
   下载图片和附件，处理命名、去重、相对路径。

7. 导出模块  
   支持 ZIP 下载、本地目录写入。

8. 报告模块  
   输出转换成功项、失败项、不可支持元素、建议手工调整项。

## 12. 技术方案建议

推荐架构：

```text
Chrome Extension
  popup / side panel
  content script
  service worker
  converter engine
  exporter

Optional Native Helper
  local file writing
  latex compile
  git operations
```

MVP 优先不做 Native Helper，直接使用 ZIP 下载和 File System Access API。若后续需要自动编译、Git 提交、写入任意路径，可增加 Native Messaging。本地原生程序可通过 Chrome Native Messaging 与插件通信，但需要安装并注册 native messaging host。

## 13. 权限要求

Chrome 插件权限：

- `activeTab`：识别当前页面。
- `scripting`：注入 content script。
- `downloads`：下载 ZIP。
- `storage`：保存用户配置。
- 飞书相关 host permissions：访问飞书文档域名和开放接口域名。
- 可选 `nativeMessaging`：后续本地助手版本使用。

## 14. 用户配置

用户可配置：

- 文档类型：文章、论文、报告、书籍章节。
- 编译引擎：XeLaTeX / LuaLaTeX。
- 中文模板：`ctexart` / `ctexrep` / 自定义模板。
- 图片策略：原图 / 压缩 / WebP 转 PNG。
- 代码块方案：`listings` / `minted`。
- 表格方案：普通 `tabularx` / 跨页 `longtable`。
- 文件拆分策略：单文件 / 按一级标题拆分。
- 是否生成目录。
- 是否保留转换注释。

## 15. 错误处理

常见错误：

- 未登录飞书：提示登录。
- 当前页面不是飞书文档：提示打开文档页。
- 无文档权限：提示申请权限。
- 图片下载失败：保留占位并写入报告。
- 表格过复杂：降级为简化表格或图片占位。
- 公式解析失败：保留原始公式文本。
- 本地目录无写权限：要求重新选择目录。

## 16. 成功指标

产品指标：

- 单篇普通文档导出耗时 < 30 秒。
- 生成项目首次编译成功率 >= 90%。
- 用户手工修复时间相比手动复制降低 70% 以上。
- P0 元素转换失败率 < 5%。
- 转换报告覆盖率 100%，所有失败元素都有定位和原因。

## 17. 里程碑

### MVP，2-4 周

- Chrome 插件基础框架。
- 当前文档识别。
- 基础 block 到 TeX 转换。
- 图片下载。
- ZIP 导出。
- 转换报告。

### V1，4-8 周

- 本地目录写入。
- 表格增强。
- 公式增强。
- 模板配置。
- 样式映射配置。

### V2，8 周以上

- Native Helper。
- 本地自动编译。
- PDF 预览对比。
- Git/Overleaf 集成。
- 团队模板库。

## 18. 主要风险

最大风险是“格式尽量完全一致”这个目标本身。飞书是 Web 富文本文档，LaTeX 是排版语言，两者模型不同。建议产品承诺分层表达：

- 内容完整：必须做到。
- 结构一致：必须做到。
- 主要视觉一致：尽量做到。
- 像素级一致：不承诺，只对导出的 PDF 做近似对比。

第二个风险是数据获取方式。如果只解析页面 DOM，稳定性差；如果用开放 API，样式细节可能不完整。因此建议采用“开放 API 为主，页面辅助解析为辅”的双通道方案。

## 19. MVP 验收用例

至少准备 10 篇测试文档：

- 纯文本长文档。
- 多级标题文档。
- 中英文混排文档。
- 多图片文档。
- 复杂列表文档。
- 代码块文档。
- 数学公式文档。
- 普通表格文档。
- callout / 引用块文档。
- 包含不支持嵌入对象的文档。

每篇文档验收：

- ZIP 可正常下载。
- 项目结构完整。
- `main.tex` 可编译。
- 图片路径正确。
- 转换报告准确。
- 不支持元素没有静默丢失。
