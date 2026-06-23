# Feishu to TeX

飞书文档转 LaTeX 项目的 CLI 工具。

## 依赖

- Python 3.7+
- [lark-cli](https://github.com/larksuite/lark-cli) - 飞书 CLI 工具
- 已登录飞书账号: `lark-cli auth login`

## 安装

```bash
# 安装 lark-cli (如果还没有)
brew install larksuite/tap/lark-cli

# 登录飞书
lark-cli auth login
```

## 使用

```bash
# 方式1: 使用 convert.py 脚本
python3 convert.py <飞书文档URL> [输出目录]

# 方式2: 使用模块
python3 -m feishu2tex <飞书文档URL> [输出目录]

# 示例
python3 convert.py https://xxx.feishu.cn/docx/Z1Fj...tnAc ./test
```

## 项目结构

```
feishu2tex/
├── __init__.py     # 包初始化
├── __main__.py     # CLI 入口
├── feishu.py       # 飞书文档获取与解析
├── tex.py          # LaTeX 生成
├── project.py      # 项目生成
└── utils.py        # 工具函数
```

## 转换能力

- 标题 (H1-H6)，自动去掉数字序号
- 段落、粗体、斜体、链接
- 有序/无序列表、待办事项
- 代码块 (保留语言标识)
- 表格
- 引用、高亮框 (callout)
- 图片 (自动下载)
- 数学公式 (行内)
- 特殊符号 (≤, ≥ 等)

## 输出结构

```
doc-title/
├── main.tex              # 主文件
├── sections/             # 章节文件
│   ├── 01-intro.tex
│   └── 02-content.tex
├── assets/
│   └── images/           # 下载的图片
├── styles/
│   └── feishu.sty        # 样式文件
├── latexmkrc             # latexmk 配置
├── metadata.json         # 文档元数据
└── conversion-report.json # 转换报告
```

## 编译

上传项目目录到 [Overleaf](https://overleaf.com)，选择 XeLaTeX 编译器。

本地编译:
```bash
cd doc-title
xelatex main.tex
xelatex main.tex  # 运行两次生成目录
```

## 测试

测试文件放在 `test/` 目录，每个文档自成一个子文件夹。

```bash
python3 convert.py <URL> ./test
```

## 已知限制

- 需要飞书账号有文档访问权限
- 嵌入的电子表格/多维表格不会转换
- 画板/白板不会转换
- 部分复杂排版可能需要手动调整
