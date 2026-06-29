"""LaTeX 生成"""

import re

from .utils import escape_tex, strip_heading_number, sanitize_ascii
from .table import generate_table_tex
from .image import generate_image_tex
from .callout import generate_callout_tex


def generate_tex(blocks, section_heading=None):
    """将块列表转换为 TeX 内容"""
    lines = []
    in_list = None
    image_count = 0
    table_count = 0
    current_section_num = None
    
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
            cmd = ['chapter', 'section', 'subsection', 'subsubsection', 
                   'paragraph', 'subparagraph'][max(0, min(level - 1, 5))]
            heading_text = escape_tex(strip_heading_number(block["content"]))
            if heading_text:
                # 在 chapter 前用 cleardoublepage（奇数页开始）
                if level == 1:
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
            # 跳过已用作表格 caption 的段落
            if block.get('used'):
                continue
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
            # listings 不支持的语言设为空
            unsupported = ['plaintext', 'text', 'plain']
            if safe_lang.lower() in unsupported:
                safe_lang = ''
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
            lines.extend(generate_callout_tex(block))
        
        elif block_type == 'divider':
            lines.append('\\noindent\\rule{\\textwidth}{0.4pt}')
            lines.append('')
        
        elif block_type == 'image':
            src = block.get('src', '')
            alt = block.get('alt', '')
            local_path = block.get('local_path', '')
            if local_path:
                image_count += 1
                lines.extend(generate_image_tex(local_path, alt, image_count))
            elif src:
                lines.append(f'% [图片: {alt or src}]')
            lines.append('')
        
        elif block_type == 'table':
            rows = block.get('rows', [])
            if rows:
                table_count += 1
                # 使用表格自带的 caption，如果没有则自动生成
                if 'caption' in block:
                    caption = escape_tex(block['caption'])
                elif current_section_num:
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
    
    # 在章节末尾插入 FloatBarrier，阻止表格跨章节浮动
    lines.append('')
    lines.append('\\FloatBarrier')
    
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
        '\\pagestyle{empty}',
        '',
        f'\\title{{{escape_tex(title)}}}',
        '\\author{}',
        '\\date{\\today}',
        '',
        '\\begin{document}',
        '',
        '% ===== 封面 =====',
        '\\begin{titlepage}',
        '  \\thispagestyle{empty}',
        '  \\begin{tikzpicture}[remember picture, overlay]',
        '    % 顶部装饰条',
        '    \\fill[gray!40] (current page.north west) rectangle ([yshift=-4cm]current page.north east);',
        '    \\fill[gray!60] ([yshift=-4cm]current page.north west) rectangle ([yshift=-4.3cm]current page.north east);',
        '    % 底部装饰条',
        '    \\fill[gray!40] (current page.south west) rectangle ([yshift=2cm]current page.south east);',
        '    \\fill[gray!60] ([yshift=2cm]current page.south west) rectangle ([yshift=2.3cm]current page.south east);',
        '    % 侧边装饰线',
        '    \\fill[gray!30] ([xshift=2cm]current page.north west) rectangle ([xshift=2.15cm]current page.south west);',
        '    \\fill[gray!30] ([xshift=-2cm]current page.north east) rectangle ([xshift=-2.15cm]current page.south east);',
        '    % 标题（在顶部装饰条内）',
        '    \\node[anchor=center, text=white, font=\\Huge\\bfseries] at ([yshift=-2cm]current page.north) {\\parbox{0.85\\textwidth}{\\centering ' + escape_tex(title) + '}};',
        '    % 日期',
        '    \\node[anchor=center, text=gray!70!white, font=\\Large] at ([yshift=1cm]current page.center) {\\today};',
        '  \\end{tikzpicture}',
        '\\end{titlepage}',
        '',
        '% ===== 目录 =====',
        '\\tableofcontents',
        '\\thispagestyle{empty}',
        '\\cleardoublepage',
        '',
        '% ===== 正文开始，页码从1开始 =====',
        '\\cleardoublepage',
        '\\pagestyle{plain}',
        '\\pagenumbering{arabic}',
        '\\setcounter{page}{1}',
        '',
        '% 自定义cleardoublepage，空白页无页码',
        '\\makeatletter',
        '\\renewcommand{\\cleardoublepage}{',
        '  \\clearpage',
        '  \\if@twoside',
        '    \\ifodd\\c@page',
        '      \\else',
        '        \\thispagestyle{empty}',
        '        \\hbox{}',
        '        \\newpage',
        '        \\if@twocolumn',
        '          \\hbox{}',
        '          \\newpage',
        '        \\fi',
        '      \\fi',
        '  \\fi',
        '}',
        '\\makeatother',
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
    lines.append('\\begin{tikzpicture}[remember picture, overlay]')
    lines.append('  % 顶部装饰条')
    lines.append('  \\fill[gray!40] (current page.north west) rectangle ([yshift=-3cm]current page.north east);')
    lines.append('  \\fill[gray!60] ([yshift=-3cm]current page.north west) rectangle ([yshift=-3.3cm]current page.north east);')
    lines.append('  % 底部装饰条')
    lines.append('  \\fill[gray!40] (current page.south west) rectangle ([yshift=2cm]current page.south east);')
    lines.append('  \\fill[gray!60] ([yshift=2cm]current page.south west) rectangle ([yshift=2.3cm]current page.south east);')
    lines.append('  % 标题')
    lines.append('  \\node[anchor=center, text=white, font=\\Huge\\bfseries] at (current page.center) {\\parbox{0.85\\textwidth}{\\centering ' + escape_tex(title) + '}};')
    lines.append('\\end{tikzpicture}')
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
\RequirePackage{float}
\RequirePackage{placeins}
\RequirePackage{adjustbox}
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

% 浮动体参数优化：底部优先于顶部（与图片 minipage 策略一致）
\renewcommand{\topfraction}{0.7}
\renewcommand{\bottomfraction}{0.9}
\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.85}
\setcounter{topnumber}{2}
\setcounter{bottomnumber}{3}
\setcounter{totalnumber}{5}

% 表格样式：垂直居中 + 左对齐
\newcolumntype{X}{>{\RaggedRight\arraybackslash}m{\hsize}}

% chapter 标题样式：减少顶部间距
\ctexset{
  chapter/beforeskip=-10pt,
  chapter/afterskip=30pt,
}

""" + generate_callout_style()


def generate_latexmkrc():
    """生成 latexmkrc"""
    return """$pdf_mode = 5;
$xelatex = "xelatex -interaction=nonstopmode -file-line-error %O %S";
"""
