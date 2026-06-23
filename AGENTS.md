# AGENTS.md

## 项目

飞书文档转 LaTeX CLI 工具。

## 核心依赖

- Python 3.7+
- lark-cli (`brew install larksuite/tap/lark-cli`)
- 飞书账号登录: `lark-cli auth login`

## 结构

```
feishu2tex/          # 主包
├── __init__.py      # 包初始化
├── __main__.py      # CLI 入口 (python3 -m feishu2tex)
├── callout.py       # 高亮块 (Callout) 解析与生成
├── feishu.py        # 飞书 API 调用和 XML 解析
├── tex.py           # LaTeX 代码生成
├── project.py       # 项目文件夹创建
├── table.py         # 表格解析与生成
└── utils.py         # 工具函数 (转义、清理等)
convert.py           # 快捷入口脚本
test/                # 测试输出 (gitignore)
```

## 常用命令

```bash
# 转换文档
python3 convert.py <URL> ./test
python3 -m feishu2tex <URL> ./test

# 语法检查
python3 -m py_compile convert.py
python3 -m py_compile feishu2tex/__main__.py

# 编译测试
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
cd test/<项目目录>
xelatex -interaction=nonstopmode main.tex  # 第一次生成 .toc
xelatex -interaction=nonstopmode main.tex  # 第二次插入目录
```

## 关键约定

- lark-cli 命令: `lark-cli docs +fetch --api-version v2 --doc <URL> --doc-format xml --detail simple --format json`
- XML 标签: `<title>`, `<h1>-<h6>`, `<ul>/<ol>/<li>`, `<pre>/<code>`, `<img>`, `<table>`, `<callout>`, `<checkbox>`
- 按 H1/H2 分章节
- 标题序号自动去掉 (如 "1.1 跟车能力" → "跟车能力")
- 数学符号转义: `≤` → `$\leq$`, `≥` → `$\geq$`

## 注意事项

- 切换列表类型时必须关闭前一个列表 (itemize ↔ enumerate)
- 图片 URL 可能是飞书内部 URL，需要网络访问
- 测试目录 `test/` 不提交到 git
- 文件名保留中文字符
