# AGENTS.md

## 项目

飞书文档转 LaTeX CLI 工具。用法: `python3 convert.py <飞书文档URL> [输出目录]`

## 核心依赖

- Python 3.7+
- lark-cli (`brew install larksuite/tap/lark-cli`)
- 飞书账号登录: `lark-cli auth login`

## 结构

```
convert.py          # 主脚本，解析飞书 XML 并生成 LaTeX 项目
test/               # 测试输出，每个文档一个子文件夹
README.md           # 用户文档
```

## 关键约定

- 调用 `lark-cli docs +fetch --api-version v2 --doc <URL> --doc-format xml --detail simple --format json` 获取文档
- 解析 XML (标准 HTML 子集: p, h1-h6, ul, ol, table, pre, blockquote, img 等)
- 按 H1/H2 分章节，生成 `sections/01-xxx.tex`
- 图片自动下载到 `assets/images/`
- 样式文件在 `styles/feishu.sty`

## 常用命令

```bash
# 测试转换
python3 convert.py <URL> ./test

# 检查语法
python3 -m py_compile convert.py
```

## XML 格式要点

- `<title>` 是文档标题
- `<pre lang="xxx"><code>...</code></pre>` 是代码块
- `<img href="..."/>` 是图片，需要下载
- `<latex>...</latex>` 是行内公式
- `<callout>` 是高亮框
- `<checkbox done="true|false">` 是待办项

## 注意事项

- lark-cli 输出的 XML 中 `&` 已转义为 `&amp;`，不要重复转义
- 表格可能有 `<thead>` / `<tbody>`，也可能直接是 `<tr>`
- 图片 URL 可能是飞书内部 URL，需要能访问
- 测试目录 `test/` 下的文件不提交到 git
