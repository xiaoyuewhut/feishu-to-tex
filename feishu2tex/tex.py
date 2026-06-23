"""LaTeX 生成"""

import re

from .utils import escape_tex, strip_heading_number, sanitize_ascii


def generate_tex(blocks):
    """将块列表转换为 TeX 内容"""
    lines = []
    in_list = None
    
    for i, block in enumerate(blocks):
        block_type = block.get('type')
        
        # 关闭列表（当切换到不同类型或非列表类型时）
        if in_list:
            should_close = False
            if block_type == 'ordered_list' and in_list != 'ordered':
                should_close = True
            elif block_type == 'unordered_list' and in_list != 'unordered':
                should_close = True
            elif block_type == 'checkbox' and in_list != 'unchecked':
                should_close = True
            elif block_type not in ['ordered_list', 'unordered_list', 'checkbox']:
                should_close = True
            
            if should_close:
                if in_list == 'ordered':
                    lines.append('\\end{enumerate}')
                else:
                    lines.append('\\end{itemize}')
                lines.append('')
                in_list = None
        
        if block_type == 'title':
            # 标题在 main.tex 中处理
            continue
        
        elif block_type == 'heading':
            level = block.get('level', 1)
            cmd = ['section', 'subsection', 'subsubsection', 
                   'paragraph', 'subparagraph', 'subparagraph'][min(level - 1, 5)]
            heading_text = strip_heading_number(block["content"])
            if heading_text:
                lines.append(f'\\{cmd}{{{heading_text}}}')
                lines.append('')
        
        elif block_type == 'paragraph':
            lines.append(block['content'])
            lines.append('')
        
        elif block_type == 'ordered_list':
            if in_list != 'ordered':
                lines.append('\\begin{enumerate}')
                in_list = 'ordered'
            for item in block.get('items', []):
                lines.append(f'  \\item {item}')
        
        elif block_type == 'unordered_list':
            if in_list != 'unordered':
                lines.append('\\begin{itemize}')
                in_list = 'unordered'
            for item in block.get('items', []):
                lines.append(f'  \\item {item}')
        
        elif block_type == 'checkbox':
            if in_list != 'unchecked':
                lines.append('\\begin{itemize}')
                in_list = 'unchecked'
            marker = '$\\boxtimes$' if block.get('done') else '$\\square$'
            lines.append(f'  \\item[{marker}] {block["content"]}')
        
        elif block_type == 'code_block':
            lang = block.get('language', '')
            caption = block.get('caption', '')
            if caption:
                lines.append(f'\\begin{{lstlisting}}[language={lang}, caption={{{caption}}}]')
            else:
                lines.append(f'\\begin{{lstlisting}}[language={lang}]')
            lines.append(block['content'])
            lines.append('\\end{lstlisting}')
            lines.append('')
        
        elif block_type == 'quote':
            lines.append('\\begin{quote}')
            lines.append(f'  {escape_tex(block["content"])}')
            lines.append('\\end{quote}')
            lines.append('')
        
        elif block_type == 'callout':
            lines.append('\\begin{quote}')
            lines.append(f'  \\textbf{{注意:}} {escape_tex(block["content"])}')
            lines.append('\\end{quote}')
            lines.append('')
        
        elif block_type == 'divider':
            lines.append('\\noindent\\rule{\\textwidth}{0.4pt}')
            lines.append('')
        
        elif block_type == 'image':
            src = block.get('src', '')
            alt = block.get('alt', '')
            if src:
                lines.append(f'% [图片: {alt or src}]')
            lines.append('')
        
        elif block_type == 'table':
            rows = block.get('rows', [])
            if rows:
                cols = max(len(row) for row in rows)
                
                # 计算每列的总字符数和最大字符数
                col_total_chars = [0] * cols
                col_max_chars = [0] * cols
                col_counts = [0] * cols
                
                for row in rows:
                    for i, cell in enumerate(row):
                        if i < cols:
                            cell_len = len(str(cell))
                            col_total_chars[i] += cell_len
                            col_max_chars[i] = max(col_max_chars[i], cell_len)
                            if cell_len > 0:
                                col_counts[i] += 1
                
                # 计算每列的平均字符数
                col_avg_chars = []
                for i in range(cols):
                    if col_counts[i] > 0:
                        col_avg_chars.append(col_total_chars[i] / col_counts[i])
                    else:
                        col_avg_chars.append(1)
                
                # 根据平均字符数计算列宽比例
                total_avg = sum(col_avg_chars)
                col_widths = [(avg / total_avg) * 0.92 for avg in col_avg_chars]
                
                # 确保最小列宽
                min_width = 0.10
                col_widths = [max(w, min_width) for w in col_widths]
                
                # 归一化
                total_width = sum(col_widths)
                col_widths = [w / total_width for w in col_widths]
                
                lines.append('\\begin{table}[htbp]')
                lines.append('  \\centering')
                lines.append('  \\small')
                lines.append('  \\renewcommand{\\arraystretch}{1.4}')
                
                # 使用 M{} 类型实现垂直居中 + 允许换行 + 居中对齐
                col_specs = [f'M{{{w:.3f}\\textwidth}}' for w in col_widths]
                col_spec = ''.join(col_specs)
                
                lines.append(f'  \\begin{{tabular}}{{{col_spec}}}')
                lines.append('    \\toprule')
                
                # 预处理：计算每列每行的合并信息
                # merge_info[row][col] = (rowspan, content) 或 None 表示被合并
                merge_info = [[None for _ in range(cols)] for _ in range(len(rows))]
                
                for c in range(cols):
                    r = 0
                    while r < len(rows):
                        cell_val = str(rows[r][c]) if c < len(rows[r]) else ''
                        if cell_val.strip() == '':
                            # 空单元格，可能是被合并的
                            r += 1
                            continue
                        # 计算向下合并的行数
                        span = 1
                        while r + span < len(rows):
                            next_val = str(rows[r + span][c]) if c < len(rows[r + span]) else ''
                            if next_val.strip() == '':
                                span += 1
                            else:
                                break
                        if span > 1:
                            merge_info[r][c] = (span, cell_val)
                            for k in range(1, span):
                                merge_info[r + k][c] = (0, '')  # 标记为被合并
                        else:
                            merge_info[r][c] = (1, cell_val)
                        r += span
                
                # 生成表格行
                for r, row in enumerate(rows):
                    cells = []
                    skip_cols = set()
                    
                    for c in range(cols):
                        info = merge_info[r][c]
                        if info is None:
                            cells.append('')
                        elif info[0] == 0:
                            # 被合并的单元格，跳过
                            skip_cols.add(c)
                            cells.append('')
                        elif info[0] > 1:
                            # 使用 multirow 合并
                            cells.append(f'\\multirow{{{info[0]}}}{{*}}{{{escape_tex(info[1])}}}')
                        else:
                            cells.append(escape_tex(info[1]))
                    
                    if r == 0:
                        header_cells = [f'\\textbf{{{cell}}}' for cell in cells]
                        lines.append(f'    {" & ".join(header_cells)} \\\\')
                        lines.append('    \\midrule')
                    else:
                        lines.append(f'    {" & ".join(cells)} \\\\')
                
                lines.append('    \\bottomrule')
                lines.append('  \\end{tabular}')
                lines.append('\\end{table}')
                lines.append('')
    
    # 关闭最后的列表
    if in_list:
        if in_list == 'ordered':
            lines.append('\\end{enumerate}')
        else:
            lines.append('\\end{itemize}')
    
    return '\n'.join(lines)


def split_sections(blocks):
    """按 H1/H2 分章节"""
    sections = []
    current = {'heading': None, 'blocks': []}
    
    for block in blocks:
        block_type = block.get('type')
        
        # 在 H1/H2 处分割
        if block_type == 'heading' and block.get('level', 3) <= 2:
            if current['blocks']:
                sections.append(current)
                current = {'heading': None, 'blocks': []}
        
        if current['heading'] is None and block_type == 'heading':
            current['heading'] = block.get('content')
        
        current['blocks'].append(block)
    
    if current['blocks']:
        sections.append(current)
    
    if not sections:
        sections.append({'heading': 'content', 'blocks': []})
    
    return sections


def generate_main_tex(title, sections):
    """生成 main.tex"""
    lines = [
        '\\documentclass[UTF8, a4paper, 12pt]{ctexart}',
        '\\usepackage{styles/feishu}',
        '',
        f'\\title{{{escape_tex(title)}}}',
        '\\author{}',
        '\\date{\\today}',
        '',
        '\\begin{document}',
        '\\maketitle',
        '\\tableofcontents',
        '\\newpage',
        '',
    ]
    
    for i, section in enumerate(sections):
        num = str(i + 1).zfill(2)
        heading = section.get('heading')
        clean_heading = strip_heading_number(heading) if heading else None
        name = sanitize_ascii(clean_heading or 'content')
        lines.append(f'\\input{{sections/{num}-{name}}}')
        lines.append('')
    
    lines.append('\\end{document}')
    return '\n'.join(lines)


def generate_style_file():
    """生成样式文件"""
    return r"""\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{feishu}[2024/01/01 Feishu Document Style]

\RequirePackage{graphicx}
\RequirePackage{hyperref}
\RequirePackage{xcolor}
\RequirePackage{soul}
\RequirePackage{listings}
\RequirePackage{amsmath}
\RequirePackage{amssymb}
\RequirePackage{geometry}
\RequirePackage{fancyhdr}
\RequirePackage{enumitem}
\RequirePackage{booktabs}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage{ragged2e}
\RequirePackage{multirow}

\geometry{a4paper, margin=2.5cm}

\hypersetup{
  colorlinks=true,
  linkcolor=blue,
  urlcolor=blue,
}

\lstset{
  basicstyle=\ttfamily\small,
  breaklines=true,
  frame=single,
  numbers=left,
  numberstyle=\tiny,
  tabsize=4,
  showstringspaces=false,
}

\setlist{noitemsep, topsep=0pt}

% 表格样式：垂直居中 + 允许换行 + 居中对齐
\newcolumntype{Y}{>{\Centering\arraybackslash}X}
\newcolumntype{M}[1]{>{\Centering\arraybackslash}m{#1}}

"""


def generate_latexmkrc():
    """生成 latexmkrc"""
    return """$pdf_mode = 5;
$xelatex = "xelatex -interaction=nonstopmode -file-line-error %O %S";
"""
