"""飞书文档获取与解析"""

import json
import subprocess
import re
import xml.etree.ElementTree as ET

from .utils import escape_tex
from .latex import parse_latex


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


def fetch_sheet_data(token, sheet_id):
    """获取电子表格数据"""
    cmd = [
        'lark-cli', 'sheets', '+cells-get',
        '--spreadsheet-token', token,
        '--sheet-id', sheet_id,
        '--range', 'A1:Z100',
        '--format', 'json'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    
    data = json.loads(result.stdout)
    if not data.get('ok'):
        return None
    
    # 提取单元格值
    ranges = data.get('data', {}).get('ranges', [])
    if not ranges:
        return None
    
    cells = ranges[0].get('cells', [])
    rows = []
    for row in cells:
        row_values = [cell.get('value', '') for cell in row]
        # 过滤全空行
        if any(str(v).strip() for v in row_values):
            rows.append(row_values)
    
    return rows if rows else None


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
        from .callout import parse_callout
        return parse_callout(elem)
    
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
    
    if tag == 'sheet':
        sheet_id = elem.get('sheet-id', '')
        token = elem.get('token', '')
        return {'type': 'sheet', 'sheet_id': sheet_id, 'token': token}
    
    if tag == 'checkbox':
        done = elem.get('done', 'false') == 'true'
        content = get_rich_text(elem)
        return {'type': 'checkbox', 'done': done, 'content': content}
    
    # 默认作为段落处理
    content = get_text(elem)
    if content.strip():
        return {'type': 'paragraph', 'content': content}
    return None


def parse_table(table_elem):
    """解析表格，处理 rowspan/colspan 合并"""
    rows = []
    
    # 计算列数（从 colgroup 获取）
    colgroup = table_elem.find('colgroup')
    num_cols = len(colgroup.findall('col')) if colgroup is not None else 0
    
    # 收集所有行
    all_trs = []
    thead = table_elem.find('thead')
    if thead is not None:
        all_trs.extend(thead.findall('tr'))
    tbody = table_elem.find('tbody')
    if tbody is not None:
        all_trs.extend(tbody.findall('tr'))
    if not all_trs:
        all_trs = table_elem.findall('tr')
    
    # 处理 rowspan：记录需要填充的空位
    # pending[row][col] = 剩余需要跳过的行数
    pending = {}
    
    for tr in all_trs:
        row = []
        col_idx = 0
        
        for cell in tr:
            if cell.tag not in ('th', 'td'):
                continue
            
            # 跳过被 rowspan 占用的列
            while col_idx in pending and pending[col_idx] > 0:
                row.append('')
                pending[col_idx] -= 1
                if pending[col_idx] == 0:
                    del pending[col_idx]
                col_idx += 1
            
            # 获取 rowspan
            rowspan = int(cell.get('rowspan', '1'))
            
            # 添加单元格内容
            row.append(get_text(cell))
            
            # 如果 rowspan > 1，记录需要跳过的行数
            if rowspan > 1:
                pending[col_idx] = rowspan - 1
            
            col_idx += 1
        
        # 填充剩余被 rowspan 占用的列
        while col_idx in pending and pending[col_idx] > 0:
            row.append('')
            pending[col_idx] -= 1
            if pending[col_idx] == 0:
                del pending[col_idx]
            col_idx += 1
        
        # 补齐到固定列数
        while num_cols > 0 and len(row) < num_cols:
            row.append('')
        
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
            parts.append(parse_latex(child))
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
