"""LaTeX 生成"""

import re

from .utils import escape_tex, strip_heading_number, sanitize_ascii
from .table import generate_table_tex


def generate_tex(blocks, section_heading=None):
    """将块列表转换为 TeX 内容"""
    lines = []
    in_list = None
    image_count = 0
    table_count = 0
    current_section_num = None
    
    import re
    
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
            heading_text = escape_tex(strip_heading_number(block["content"]))
            if heading_text:
                # 在 section 前用 cleardoublepage（奇数页开始）
                if level <= 2:
                    lines.append('\\cleardoublepage')
                lines.append(f'\\{cmd}{{{heading_text}}}')
                lines.append('')
            
            # 更新当前章节序号，重置表格计数器
            m = re.match(r'^([\d]+(\.[\d]+)*\.?)\s*', block["content"])
            if m:
                new_section_num = m.group(1).rstrip('.')
                if new_section_num != current_section_num:
                    current_section_num = new_section_num
                    table_count = 0
        
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
            # 只保留安全字符作为语言名
            safe_lang = re.sub(r'[^a-zA-Z0-9#+-]', '', lang) if lang else ''
            if caption:
                lines.append(f'\\begin{{lstlisting}}[language={safe_lang}, caption={{{escape_tex(caption)}}}]')
            else:
                lines.append(f'\\begin{{lstlisting}}[language={safe_lang}]')
            lines.append(block['content'])
            lines.append('\\end{lstlisting}')
            lines.append('')
        
        elif block_type == 'quote':
            lines.append('\\begin{quote}')
            lines.append(f'  {escape_tex(block["content"])}')
            lines.append('\\end{quote}')
            lines.append('')
        
        elif block_type == 'callout':
            from .callout import generate_callout_tex
            lines.extend(generate_callout_tex(block))
        
        elif block_type == 'divider':
            lines.append('\\noindent\\rule{\\textwidth}{0.4pt}')
            lines.append('')
        
        elif block_type == 'image':
            src = block.get('src', '')
            alt = block.get('alt', '')
            local_path = block.get('local_path', '')
            if local_path:
                lines.append('\\begin{figure}[htbp]')
                lines.append('  \\centering')
                lines.append(f'  \\includegraphics[width=\\textwidth, height=0.7\\textheight, keepaspectratio]{{{local_path}}}')
                # 有真实 caption 时保留，否则留空让 LaTeX 自动编号
                if alt and not re.match(r'^(paste|image|img|图片|截图|Pasted image).*$', alt, re.IGNORECASE):
                    lines.append(f'  \\caption{{{escape_tex(alt)}}}')
                else:
                    lines.append('  \\caption{}')
                lines.append('\\end{figure}')
            elif src:
                lines.append(f'% [图片: {alt or src}]')
            lines.append('')
        
        elif block_type == 'table':
            rows = block.get('rows', [])
            if rows:
                table_count += 1
                # 生成 caption: 章节序号 + 表编号
                if current_section_num:
                    caption = f'{current_section_num} 表{table_count}'
                else:
                    caption = f'表{table_count}'
                lines.append(generate_table_tex(rows, caption))
    
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
        '\\documentclass[UTF8, a4paper, 12pt, twoside, openright]{ctexbook}',
        '\\usepackage{styles/feishu}',
        '\\raggedbottom',
        '',
        f'\\title{{{escape_tex(title)}}}',
        '\\author{}',
        '\\date{\\today}',
        '',
        '\\begin{document}',
        '',
        '% ===== 封面 =====',
        '\\begin{titlepage}',
        '  \\centering',
        '  \\vspace*{2cm}',
        '  \\rule{\\textwidth}{1pt}',
        '  \\vspace{1cm}',
        '  {\\Huge\\bfseries ' + escape_tex(title) + '\\\\}',
        '  \\vspace{1cm}',
        '  \\rule{\\textwidth}{1pt}',
        '  \\vspace{3cm}',
        '  {\\Large\\today\\\\}',
        '  \\vfill',
        '\\end{titlepage}',
        '',
        '% ===== 目录 =====',
        '\\tableofcontents',
        '\\cleardoublepage',
        '',
    ]
    
    for i, section in enumerate(sections):
        num = str(i + 1).zfill(2)
        heading = section.get('heading')
        clean_heading = strip_heading_number(heading) if heading else None
        name = sanitize_ascii(clean_heading or 'content')
        lines.append(f'\\input{{sections/{num}-{name}}}')
        lines.append('')
    
    # ===== 封底 =====
    lines.append('% ===== 封底 =====')
    lines.append('\\cleardoublepage')
    lines.append('\\thispagestyle{empty}')
    lines.append('\\vspace*{\\fill}')
    lines.append('\\begin{center}')
    lines.append('  \\rule{0.5\\textwidth}{1pt}')
    lines.append('  \\vspace{1cm}')
    lines.append('  {\\Huge\\bfseries ' + escape_tex(title) + '\\\\}')
    lines.append('  \\vspace{1cm}')
    lines.append('  \\rule{0.5\\textwidth}{1pt}')
    lines.append('\\end{center}')
    lines.append('\\vspace*{\\fill}')
    lines.append('')
    lines.append('\\end{document}')
    return '\n'.join(lines)


def generate_style_file():
    """生成样式文件"""
    from .callout import generate_callout_style
    
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
\RequirePackage{longtable}
\RequirePackage{tcolorbox}
\RequirePackage{tabularray}
\RequirePackage{needspace}
\UseTblrLibrary{booktabs}

\geometry{a4paper, margin=2.5cm}

\hypersetup{
  colorlinks=true,
  linkcolor=blue,
  urlcolor=blue,
  bookmarksnumbered=true,
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

% 浮动体参数优化：减少图片跳页
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.85}
\setcounter{topnumber}{3}
\setcounter{bottomnumber}{2}
\setcounter{totalnumber}{5}

% 表格样式：垂直居中 + 左对齐
\newcolumntype{X}{>{\RaggedRight\arraybackslash}m{\hsize}}

""" + generate_callout_style()


def generate_latexmkrc():
    """生成 latexmkrc"""
    return """$pdf_mode = 5;
$xelatex = "xelatex -interaction=nonstopmode -file-line-error %O %S";
"""
