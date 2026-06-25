# AGENTS.md

## 项目

飞书文档转 LaTeX CLI 工具。

## 核心约束

- **所有改进必须面向通用场景**，不能针对某个文档做单独优化
- 设计时考虑：任意飞书文档、任意表格结构、任意图片数量、任意章节深度

## 核心依赖

- Python 3.7+
- lark-cli (`brew install larksuite/tap/lark-cli`)
- 飞书账号登录: `lark-cli auth login`
- TinyTeX 需安装: `tabularray`, `tcolorbox`, `needspace`

## 结构

```
feishu2tex/          # 主包
├── __init__.py      # 包初始化
├── __main__.py      # CLI 入口 (python3 -m feishu2tex)
├── callout.py       # 高亮块 (Callout) 解析与生成
├── feishu.py        # 飞书 API 调用和 XML 解析
├── tex.py           # LaTeX 代码生成
├── project.py       # 项目文件夹创建
├── table.py         # 表格解析与生成 (tabularray)
└── utils.py         # 工具函数 (转义、清理等)
convert.py           # 快捷入口脚本
test/                # 测试输出 (gitignore)
```

## 常用命令

```bash
# 转换文档
python3 convert.py <URL> ./test

# 语法检查
python3 -m py_compile feishu2tex/table.py
python3 -m py_compile feishu2tex/tex.py

# 编译测试
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
cd test/<项目目录>
xelatex -interaction=nonstopmode main.tex  # 第一次生成 .toc
xelatex -interaction=nonstopmode main.tex  # 第二次插入目录
```

## 关键设计决策

### 表格 (table.py)
- 使用 `tabularray` 的 `longtblr` 环境，X 列自动分配宽度
- 合并逻辑：指标-权重成对合并（权重列只能跟随对应指标列范围）
- 大跨度合并保留，不做 MAX_ROW_SPAN 限制

### 图片 (tex.py)
- 使用 `[htbp]` 浮动体，自适应尺寸（宽度撑满，高度限制 0.7\textheight）
- 无 caption 时留空 `\caption{}`，让 LaTeX 自动编号
- 有 caption 时保留原样

### 特殊字符 (utils.py)
- escape_tex() 处理 TeX 特殊字符和 Unicode 符号（★☆●○→←等）
- 标题和 icon 都必须经过 escape_tex() 转义

## 注意事项

- 切换列表类型时必须关闭前一个列表 (itemize ↔ enumerate)
- 图片 URL 可能是飞书内部 URL，需要网络访问
- 测试目录 `test/` 不提交到 git
- 文件名保留中文字符
- lark-cli API 偶尔会返回 "Internal error"，需要重试
