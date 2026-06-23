#!/usr/bin/env python3
"""
飞书文档转 LaTeX CLI 工具
用法: python3 convert.py <飞书文档URL> [输出目录]
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


def run_lark_cli(url):
    """调用 lark-cli 获取文档内容"""
    cmd = [
        'lark-cli', 'docs', '+fetch',
        '--api-version', 'v2',
        '--doc', url,
        '--doc-format', 'xml',
        '--detail', 'simple',
        '--format', 'json'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f'lark-cli 调用失败: {result.stderr}')
    return json.loads(result.stdout)


def extract_doc_info(response):
    """从 lark-cli 响应中提取文档信息"""
    doc = response.get('data', {}).get('document', {})
    content = doc.get('content', '')
    doc_id = doc.get('document_id', 'unknown')
    return doc_id, content


def parse_xml_content(xml_content):
    """解析 XML 内容为块列表"""
    blocks = []
    
    # 包裹在根元素中
    wrapped = f'<root>{xml_content}</root>'
    
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError as e:
        print(f'XML 解析错误: {e}')
        # 尝试修复常见问题
        xml_content = xml_content.replace('&', '&amp;')
        wrapped = f'<root>{xml_content}</root>'
        try:
            root = ET.fromstring(wrapped)
        except:
            return blocks
    
    for elem in root:
        block = parse_element(elem)
        if block:
            blocks.append(block)
    
    return blocks


def parse_element(elem):
    """解析单个 XML 元素为块"""
    tag = elem.tag
    
    if tag == 'title':
        return {'type': 'title', 'content': get_text(elem), 'level': 0}
    
    if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(tag[1])
        return {'type': 'heading', 'level': level, 'content': get_text(elem)}
    
    if tag == 'p':
        content = get_rich_text(elem)
        if content.strip():
            return {'type': 'paragraph', 'content': content}
        return None
    
    if tag == 'ul':
        items = []
        for li in elem.findall('li'):
            items.append(get_rich_text(li))
        return {'type': 'unordered_list', 'items': items}
    
    if tag == 'ol':
        items = []
        for li in elem.findall('li'):
            items.append(get_rich_text(li))
        return {'type': 'ordered_list', 'items': items}
    
    if tag == 'pre':
        code_elem = elem.find('code')
        lang = elem.get('lang', '')
        caption = elem.get('caption', '')
        code = code_elem.text if code_elem is not None else elem.text or ''
        return {'type': 'code_block', 'language': lang, 'content': code, 'caption': caption}
    
    if tag == 'blockquote':
        content = get_text(elem)
        return {'type': 'quote', 'content': content}
    
    if tag == 'callout':
        content = get_text(elem)
        return {'type': 'callout', 'content': content}
    
    if tag == 'hr':
        return {'type': 'divider'}
    
    if tag == 'img':
        src = elem.get('href', elem.get('src', ''))
        alt = elem.get('caption', elem.get('name', ''))
        width = elem.get('width', '')
        height = elem.get('height', '')
        return {'type': 'image', 'src': src, 'alt': alt, 'width': width, 'height': height}
    
    if tag == 'table':
        return parse_table(elem)
    
    if tag == 'checkbox':
        done = elem.get('done', 'false') == 'true'
        content = get_text(elem)
        return {'type': 'checkbox', 'done': done, 'content': content}
    
    # 默认作为段落处理
    content = get_text(elem)
    if content.strip():
        return {'type': 'paragraph', 'content': content}
    return None


def parse_table(table_elem):
    """解析表格"""
    rows = []
    
    # 处理 thead
    thead = table_elem.find('thead')
    if thead is not None:
        for tr in thead.findall('tr'):
            row = []
            for th in tr.findall('th'):
                row.append(get_text(th))
            rows.append(row)
    
    # 处理 tbody
    tbody = table_elem.find('tbody')
    if tbody is not None:
        for tr in tbody.findall('tr'):
            row = []
            for td in tr.findall('td'):
                row.append(get_text(td))
            rows.append(row)
    
    # 如果没有 thead/tbody，直接处理 tr
    if not rows:
        for tr in table_elem.findall('tr'):
            row = []
            for cell in tr.findall(['th', 'td']):
                row.append(get_text(cell))
            rows.append(row)
    
    return {'type': 'table', 'rows': rows}


def get_text(elem):
    """获取元素的纯文本内容"""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.append(get_text(child))
        if child.tail:
            parts.append(child.tail)
    return ''.join(parts).strip()


def get_rich_text(elem):
    """获取富文本内容（保留格式标记）"""
    parts = []
    if elem.text:
        parts.append(escape_tex(elem.text))
    
    for child in elem:
        tag = child.tag
        child_text = get_rich_text(child)
        
        if tag == 'b' or tag == 'strong':
            parts.append(f'\\textbf{{{child_text}}}')
        elif tag == 'em' or tag == 'i':
            parts.append(f'\\textit{{{child_text}}}')
        elif tag == 'u':
            parts.append(f'\\underline{{{child_text}}}')
        elif tag == 'del' or tag == 's':
            parts.append(f'\\sout{{{child_text}}}')
        elif tag == 'code':
            parts.append(f'\\texttt{{{child_text}}}')
        elif tag == 'a':
            href = child.get('href', '')
            parts.append(f'\\href{{{href}}}{{{child_text}}}')
        elif tag == 'latex':
            parts.append(f'${child.text or ""}$')
        elif tag == 'span':
            text_color = child.get('text-color', '')
            if text_color:
                parts.append(f'\\textcolor{{{text_color}}}{{{child_text}}}')
            else:
                parts.append(child_text)
        elif tag == 'img':
            src = child.get('href', child.get('src', ''))
            parts.append(f'[图片: {src}]')
        else:
            parts.append(child_text)
        
        if child.tail:
            parts.append(escape_tex(child.tail))
    
    return ''.join(parts)


def strip_heading_number(text):
    """去掉标题开头的数字序号，如 '1.1 xxx' -> 'xxx', '2.' -> '2'"""
    # 匹配开头的数字序号: 1. / 1.1 / 1.1.1 / 1.1.1.1 等
    m = re.match(r'^([\d]+(\.[\d]+)*\.?)\s*', text)
    if m:
        rest = text[m.end():].strip()
        # 如果去掉序号后为空，保留数字部分（去掉末尾的点）
        if not rest:
            return m.group(1).rstrip('.')
        return rest
    return text


def escape_tex(text):
    """转义 TeX 特殊字符"""
    if not text:
        return ''
    # 先处理反斜杠
    text = text.replace('\\', '\\textbackslash{}')
    # 处理数学符号
    text = text.replace('≤', '$\\leq$')
    text = text.replace('≥', '$\\geq$')
    text = text.replace('＜', '$<$')
    text = text.replace('＞', '$>$')
    # 处理特殊字符
    special_chars = {
        '&': '\\&',
        '%': '\\%',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}',
    }
    for char, replacement in special_chars.items():
        text = text.replace(char, replacement)
    # 合并多余空格
    text = re.sub(r' {2,}', ' ', text)
    return text


def sanitize_filename(name):
    """清理文件名"""
    if not name:
        return 'untitled'
    # 移除不安全字符
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', name)
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    return name[:80] or 'untitled'


def sanitize_ascii(name):
    """清理文件名，保留中文和ASCII字符"""
    if not name:
        return ''
    # 保留中文、字母、数字、点、连字符
    name = re.sub(r'[^\w.\-\u4e00-\u9fff]', '-', name)
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    return name[:80]


def to_folder_name(title, doc_id):
    """生成文件夹名"""
    slug = sanitize_ascii(title)
    if len(slug) >= 3:
        return slug
    return doc_id or f'doc-{os.getpid()}'


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
            if in_list != 'unordered':
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
            lines.append(f'  {block["content"]}')
            lines.append('\\end{quote}')
            lines.append('')
        
        elif block_type == 'callout':
            lines.append('\\begin{quote}')
            lines.append(f'  \\textbf{{注意:}} {block["content"]}')
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
                lines.append('\\begin{table}[htbp]')
                lines.append('  \\centering')
                lines.append(f'  \\begin{{tabular}}{{{"l" * cols}}}')
                lines.append('    \\hline')
                for r, row in enumerate(rows):
                    cells = [escape_tex(cell) for cell in row]
                    # 补齐空单元格
                    while len(cells) < cols:
                        cells.append('')
                    lines.append(f'    {" & ".join(cells)} \\\\')
                    if r == 0:
                        lines.append('    \\hline')
                lines.append('    \\hline')
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

"""


def generate_latexmkrc():
    """生成 latexmkrc"""
    return """$pdf_mode = 5;
$xelatex = "xelatex -interaction=nonstopmode -file-line-error %O %S";
"""


def download_image(url, output_path):
    """下载图片"""
    import urllib.request
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f'  图片下载失败: {url} ({e})')
        return False


def guess_image_ext(url):
    """猜测图片扩展名"""
    parsed = urlparse(url)
    path = parsed.path.lower()
    if '.png' in path:
        return '.png'
    elif '.jpg' in path or '.jpeg' in path:
        return '.jpg'
    elif '.gif' in path:
        return '.gif'
    elif '.webp' in path:
        return '.webp'
    elif '.svg' in path:
        return '.svg'
    return '.png'


def create_project(blocks, title, doc_id, output_dir):
    """创建 LaTeX 项目"""
    # 生成文件夹名
    folder_name = to_folder_name(title, doc_id)
    project_dir = os.path.join(output_dir, folder_name)
    
    # 创建目录结构
    os.makedirs(os.path.join(project_dir, 'sections'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'assets', 'images'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'styles'), exist_ok=True)
    
    # 下载图片
    image_map = {}
    image_idx = 0
    warnings = []
    
    for block in blocks:
        if block.get('type') == 'image' and block.get('src'):
            image_idx += 1
            num = str(image_idx).zfill(3)
            ext = guess_image_ext(block['src'])
            filename = f'image-{num}{ext}'
            filepath = os.path.join(project_dir, 'assets', 'images', filename)
            
            if download_image(block['src'], filepath):
                image_map[block['src']] = f'assets/images/{filename}'
            else:
                warnings.append(f'图片下载失败: {block["src"]}')
                image_map[block['src']] = None
    
    # 替换图片引用
    for block in blocks:
        if block.get('type') == 'image' and block.get('src'):
            local_path = image_map.get(block['src'])
            if local_path:
                block['local_path'] = local_path
    
    # 分章节
    sections = split_sections(blocks)
    
    # 生成 main.tex
    main_tex = generate_main_tex(title, sections)
    with open(os.path.join(project_dir, 'main.tex'), 'w', encoding='utf-8') as f:
        f.write(main_tex)
    
    # 生成各章节
    for i, section in enumerate(sections):
        num = str(i + 1).zfill(2)
        heading = section.get('heading')
        # 去掉标题中的序号，用于文件名
        clean_heading = strip_heading_number(heading) if heading else None
        name = sanitize_ascii(clean_heading or 'content')
        filename = f'{num}-{name}.tex'
        
        section_tex = generate_tex(section.get('blocks', []))
        with open(os.path.join(project_dir, 'sections', filename), 'w', encoding='utf-8') as f:
            f.write(section_tex)
    
    # 生成样式文件
    with open(os.path.join(project_dir, 'styles', 'feishu.sty'), 'w', encoding='utf-8') as f:
        f.write(generate_style_file())
    
    # 生成 latexmkrc
    with open(os.path.join(project_dir, 'latexmkrc'), 'w', encoding='utf-8') as f:
        f.write(generate_latexmkrc())
    
    # 生成 metadata.json
    metadata = {
        'title': title,
        'doc_id': doc_id,
        'exported_at': __import__('datetime').datetime.now().isoformat(),
        'block_count': len(blocks),
        'section_count': len(sections),
        'image_count': image_idx,
    }
    with open(os.path.join(project_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # 生成 conversion-report.json
    report = {
        'title': title,
        'doc_id': doc_id,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'total_blocks': len(blocks),
        'total_sections': len(sections),
        'total_images': image_idx,
        'downloaded_images': image_idx - len(warnings),
        'sections': [
            {
                'file': f'sections/{str(i + 1).zfill(2)}-{sanitize_ascii(strip_heading_number(section.get("heading")) if section.get("heading") else "content")}.tex',
                'blocks': len(section.get('blocks', []))
            }
            for i, section in enumerate(sections)
        ],
        'warnings': warnings
    }
    with open(os.path.join(project_dir, 'conversion-report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return project_dir, folder_name


def main():
    if len(sys.argv) < 2:
        print('用法: python3 convert.py <飞书文档URL> [输出目录]')
        print('')
        print('示例:')
        print('  python3 convert.py https://xxx.feishu.cn/docx/Z1Fj...tnAc')
        print('  python3 convert.py https://xxx.feishu.cn/wiki/xxx ./output')
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    print(f'正在获取文档: {url}')
    
    try:
        # 调用 lark-cli
        response = run_lark_cli(url)
        doc_id, content = extract_doc_info(response)
        
        print(f'文档 ID: {doc_id}')
        print(f'内容长度: {len(content)} 字符')
        
        # 解析 XML
        blocks = parse_xml_content(content)
        print(f'解析到 {len(blocks)} 个内容块')
        
        if not blocks:
            print('错误: 未能解析到任何内容')
            sys.exit(1)
        
        # 获取标题
        title = 'untitled'
        for block in blocks:
            if block.get('type') == 'title':
                title = block.get('content', 'untitled')
                break
            elif block.get('type') == 'heading' and block.get('level') == 1:
                title = block.get('content', 'untitled')
                break
        
        print(f'文档标题: {title}')
        
        # 创建项目
        print('正在生成 LaTeX 项目...')
        project_dir, folder_name = create_project(blocks, title, doc_id, output_dir)
        
        print(f'\n✓ 完成!')
        print(f'  项目目录: {project_dir}')
        print(f'\n上传 {project_dir} 到 Overleaf 即可编译')
        
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
