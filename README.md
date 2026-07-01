<div align="center">

# 📄 Feishu to TeX

**将飞书文档一键转换为精美 LaTeX 项目的 CLI 工具**

[![Python](https://img.shields.io/badge/Python-3.7+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LaTeX](https://img.shields.io/badge/LaTeX-XeLaTeX-008080?logo=latex&logoColor=white)](https://www.latex-project.org/)

*告别手动排版，让飞书文档秒变专业论文*

</div>

---

## ✨ 特性亮点

| 特性 | 描述 |
|:---:|:---|
| 📝 **智能标题** | 自动识别 H1-H6 标题层级，去掉数字序号 |
| 📊 **表格处理** | 智能合并单元格、自适应缩放、固定位置显示 |
| 🖼️ **图片下载** | 自动下载文档中的图片并嵌入 LaTeX |
| 📐 **公式转换** | 行内公式自动处理，中文包裹 `\text{}` |
| 📋 **列表支持** | 有序/无序列表、待办事项完美转换 |
| 💬 **高亮框** | Callout 块转换为精美 tcolorbox |
| 🔤 **代码块** | 保留语言标识，支持语法高亮 |
| 📖 **自动目录** | 生成完整目录结构，支持交叉引用 |

---

## 🚀 快速开始

### 环境准备

```bash
# 安装 lark-cli
brew install larksuite/tap/lark-cli

# 登录飞书账号
lark-cli auth login
```

### 一键转换

```bash
# 基本用法
python3 convert.py <飞书文档URL> [输出目录]

# 示例
python3 convert.py https://xxx.feishu.cn/docx/Z1Fj...tnAc ./test

# 使用模块方式
python3 -m feishu2tex <飞书文档URL> [输出目录]
```

---

## 📁 项目结构

```
feishu2tex/
├── __init__.py      # 包初始化
├── __main__.py      # CLI 入口
├── feishu.py        # 飞书 API 调用与 XML 解析
├── tex.py           # LaTeX 代码生成
├── project.py       # 项目文件夹创建
├── table.py         # 表格解析与生成 (tabularray)
├── latex.py         # 公式块处理
├── callout.py       # 高亮块解析与生成
└── utils.py         # 工具函数 (转义、清理等)
```

---

## 📋 转换能力

<div align="center">

| 类型 | 支持内容 |
|:---:|:---|
| **标题** | H1-H6 层级，自动去序号，章节分页 |
| **文本** | 段落、粗体、斜体、下划线、删除线、链接 |
| **列表** | 有序列表、无序列表、待办事项 |
| **表格** | 智能合并、自适应缩放、浮动位置优化 |
| **图片** | 自动下载、自适应尺寸、智能编号 |
| **公式** | 行内公式、中文自动包裹 `\text{}` |
| **代码** | 保留语言标识、支持语法高亮 |
| **引用** | 引用块、高亮框 (Callout) |
| **符号** | 特殊符号 (≤, ≥, ×, ÷ 等) |

</div>

---

## 📂 输出结构

```
doc-title/
├── main.tex               # 主文件 (封面 + 目录)
├── sections/              # 章节文件
│   ├── 01-intro.tex
│   ├── 02-content.tex
│   └── ...
├── assets/
│   └── images/            # 下载的图片
├── styles/
│   └── feishu.sty         # 样式文件
├── latexmkrc              # latexmk 配置
├── metadata.json          # 文档元数据
└── conversion-report.json # 转换报告
```

---

## 🔧 编译指南

### Overleaf (推荐)

1. 下载生成的项目目录
2. 上传到 [Overleaf](https://overleaf.com)
3. 选择 **XeLaTeX** 编译器
4. 点击编译，生成精美 PDF

### 本地编译

```bash
cd doc-title

# 第一次编译 (生成 .toc)
xelatex main.tex

# 第二次编译 (插入目录)
xelatex main.tex
```

---

## 🎨 效果展示

<div align="center">

| 飞书文档 | LaTeX PDF |
|:---:|:---:|
| 在线编辑 | 专业排版 |
| 实时协作 | 精美打印 |
| 云端存储 | 本地归档 |

</div>

---

## ⚠️ 已知限制

- 🔐 需要飞书账号有文档访问权限
- 📊 电子表格支持基础单元格值转换；暂不支持合并单元格样式、公式格式、超过安全上限（5000行×100列）的数据
- 🖼️ SVG 图片自动转为 PNG（依赖 qlmanage/rsvg-convert/inkscape），非 macOS 环境可能需额外安装转换工具
- 🎨 画板/白板不会转换
- 🔧 部分复杂排版可能需要手动调整

---

## 🛠️ 技术栈

<div align="center">

| 组件 | 技术 |
|:---:|:---:|
| **语言** | Python 3.7+ |
| **飞书 API** | lark-cli |
| **LaTeX 引擎** | XeLaTeX |
| **表格** | tabularray |
| **高亮框** | tcolorbox |
| **图片** | graphicx |

</div>

---

## 📄 License

MIT License

---

<div align="center">

**Made with ❤️ by [xiaoyuewhut](https://github.com/xiaoyuewhut)**

</div>
