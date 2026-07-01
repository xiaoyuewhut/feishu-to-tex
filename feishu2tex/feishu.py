"""飞书文档获取与解析"""

import json
import subprocess
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .utils import escape_tex
from .latex import parse_latex


# ---- 重试配置 ----
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0  # 指数退避基值（秒）


@dataclass
class TableCell:
    """表格单元格，携带合并元数据。

    rowspan/colspan 为 0 表示该格是占位符（被其他格 span 覆盖），
    不应输出内容。
    """
    text: str = ''
    rowspan: int = 1
    colspan: int = 1
    is_tex: bool = False

    @property
    def is_placeholder(self) -> bool:
        return self.rowspan == 0 or self.colspan == 0

# lark-cli 超时时间（秒）
CLI_TIMEOUT = 60
# 电子表格安全上限（超过则截断并报告）
SHEET_MAX_ROWS = 5000
SHEET_MAX_COLS = 100


def _col_to_letter(n):
    """列号转字母: 1→A, 26→Z, 27→AA, 52→AZ, 53→BA, ..."""
    if n < 1:
        return 'A'
    result = ''
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _build_range(row_count, col_count):
    """根据行列数构建 A1 范围字符串: A1:{col_letter}{row_count}"""
    if col_count <= 0 or row_count <= 0:
        return 'A1:Z100'
    return f'A1:{_col_to_letter(col_count)}{row_count}'


def fetch_sheet_metadata(token, sheet_id):
    """获取电子表格元数据（行数、列数），带重试。

    返回 (row_count, column_count) 或 None。
    """
    cmd = [
        'lark-cli', 'sheets', '+workbook-info',
        '--spreadsheet-token', token,
        '--format', 'json'
    ]
    try:
        result = _run_with_retry(cmd)
        data = json.loads(result.stdout)
        sheets = data.get('data', {}).get('sheets', [])
        for s in sheets:
            if s.get('sheet_id') == sheet_id:
                return s.get('row_count', 0), s.get('column_count', 0)
        return None
    except Exception:
        return None


def _should_retry(result):
    """判断 lark-cli 结果是否需要重试。"""
    if result.returncode != 0:
        return True
    output = (result.stderr or '') + (result.stdout or '')
    if 'Internal error' in output:
        return True
    return False


def _run_with_retry(cmd, attempts=RETRY_ATTEMPTS):
    """运行 lark-cli 命令，带指数退避重试。

    对非零退出码和 "Internal error" 自动重试。
    最终失败抛出 Exception，含命令、退出码、stderr/stdout 摘要。
    """
    last_result = None
    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)
        except subprocess.TimeoutExpired:
            if attempt < attempts:
                time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                continue
            raise Exception(
                f'lark-cli 超时（{attempts}次重试后）\n'
                f'  命令: {" ".join(cmd)}')

        if not _should_retry(result):
            return result

        last_result = result
        if attempt < attempts:
            time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))

    stderr_summary = (last_result.stderr or '').strip()[:300]
    stdout_summary = (last_result.stdout or '').strip()[:300]
    raise Exception(
        f'lark-cli 调用失败（{attempts}次重试后）\n'
        f'  命令: {" ".join(cmd)}\n'
        f'  退出码: {last_result.returncode}\n'
        f'  stderr: {stderr_summary}\n'
        f'  stdout: {stdout_summary}')


def run_lark_cli(url):
    """调用 lark-cli 获取文档内容（自动重试）。"""
    cmd = [
        'lark-cli', 'docs', '+fetch',
        '--api-version', 'v2',
        '--doc', url,
        '--doc-format', 'xml',
        '--detail', 'with-ids',
        '--format', 'json'
    ]
    result = _run_with_retry(cmd)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise Exception(
            f'lark-cli 返回非 JSON:\n'
            f'  stdout: {(result.stdout or "").strip()[:300]}\n'
            f'  stderr: {(result.stderr or "").strip()[:300]}')


def extract_doc_info(response):
    """从 lark-cli 响应中提取文档信息"""
    doc = response.get('data', {}).get('document', {})
    content = doc.get('content', '')
    doc_id = doc.get('document_id', 'unknown')
    return doc_id, content


def fetch_sheet_data(token, sheet_id):
    """获取电子表格数据，按实际维度动态构建 range。

    返回 (rows, warnings) 元组：
      - rows: List[List[str]]，纯文本单元格数据
      - warnings: List[str]，截断警告列表
    """
    warnings = []

    # 1) 查元数据获取实际行列数
    meta = fetch_sheet_metadata(token, sheet_id)
    if meta:
        row_count, col_count = meta
    else:
        # 回退到安全上限
        row_count, col_count = SHEET_MAX_ROWS, SHEET_MAX_COLS
        warnings.append(f'无法获取表格 {sheet_id} 的元数据，回退到最大 {row_count} 行 × {col_count} 列')

    # 2) 检查是否需要截断
    truncated_rows = row_count > SHEET_MAX_ROWS
    truncated_cols = col_count > SHEET_MAX_COLS
    effective_rows = min(row_count, SHEET_MAX_ROWS)
    effective_cols = min(col_count, SHEET_MAX_COLS)

    if truncated_rows or truncated_cols:
        parts = []
        if truncated_rows:
            parts.append(f'行数 {row_count} → 截断至 {SHEET_MAX_ROWS}')
        if truncated_cols:
            parts.append(f'列数 {col_count} → 截断至 {SHEET_MAX_COLS}')
        warnings.append(f'表格 {sheet_id} 超出上限: {"; ".join(parts)}')

    # 3) 构建动态 range
    range_str = _build_range(effective_rows, effective_cols)

    cmd = [
        'lark-cli', 'sheets', '+cells-get',
        '--spreadsheet-token', token,
        '--sheet-id', sheet_id,
        '--range', range_str,
        '--format', 'json'
    ]
    try:
        result = _run_with_retry(cmd)
    except Exception as e:
        warnings.append(f'表格 {sheet_id} 获取失败（已重试）: {str(e)[:200]}')
        return None, warnings

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        warnings.append(f'表格 {sheet_id} JSON 解析失败')
        return None, warnings

    if not data.get('ok'):
        warnings.append(f'表格 {sheet_id} API 返回错误')
        return None, warnings

    # 4) 提取单元格值，过滤全空行
    ranges = data.get('data', {}).get('ranges', [])
    if not ranges:
        return [], warnings

    cells = ranges[0].get('cells', [])
    rows = []
    for row in cells:
        row_values = [cell.get('value', '') for cell in row]
        if any(str(v).strip() for v in row_values):
            rows.append(row_values)

    return rows, warnings


def parse_xml_content(xml_content):
    """解析 XML 内容为块列表"""
    blocks = []
    
    # 包裹在根元素中
    wrapped = f'<root>{xml_content}</root>'
    
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError as e:
        print(f'XML 解析错误: {e}')
        # 尝试修复未转义的 & 符号（不破坏已有实体）
        xml_content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', xml_content)
        wrapped = f'<root>{xml_content}</root>'
        try:
            root = ET.fromstring(wrapped)
        except ET.ParseError:
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
        raw_content = get_text(elem)
        tex_content = get_rich_text(elem)
        return {'type': 'heading', 'level': level,
                'content': tex_content, 'raw_content': raw_content}
    
    if tag == 'p':
        content = get_rich_text(elem)
        if content.strip():
            block = {'type': 'paragraph', 'content': content}
            align = elem.get('align', '')
            if align:
                block['align'] = align
            return block
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
    """解析表格，处理 rowspan/colspan 合并。

    返回 grid: List[List[TableCell]]，每个格都带有完整的
    rowspan/colspan 信息，被 span 覆盖的占位格 rowspan=colspan=0。
    """
    # 收集所有行
    all_trs = _collect_table_rows(table_elem)

    # 从 colgroup 获取声明的列数
    colgroup = table_elem.find('colgroup')
    num_cols = len(colgroup.findall('col')) if colgroup is not None else 0

    # ---- 第一遍：确定总列数 ----
    pending = {}  # col_idx -> 剩余 rowspan 行数
    max_col = 0

    for tr in all_trs:
        col_idx = 0
        for cell in tr:
            if cell.tag not in ('th', 'td'):
                continue
            # 跳过被 rowspan 占用的列
            while col_idx in pending and pending[col_idx] > 0:
                pending[col_idx] -= 1
                if pending[col_idx] == 0:
                    del pending[col_idx]
                col_idx += 1

            rowspan = int(cell.get('rowspan', '1'))
            colspan = int(cell.get('colspan', '1'))

            if rowspan > 1:
                for dc in range(colspan):
                    pending[col_idx + dc] = rowspan - 1

            col_idx += colspan

        # 尾部 pending 补位
        while col_idx in pending and pending[col_idx] > 0:
            pending[col_idx] -= 1
            if pending[col_idx] == 0:
                del pending[col_idx]
            col_idx += 1

        max_col = max(max_col, col_idx)

    total_cols = max(num_cols, max_col)

    # ---- 第二遍：构建 TableCell grid ----
    pending = {}
    grid = []

    for tr in all_trs:
        row = [TableCell('', rowspan=0, colspan=0) for _ in range(total_cols)]
        col_idx = 0

        for cell in tr:
            if cell.tag not in ('th', 'td'):
                continue

            # 跳过被 rowspan 占用的列，填占位符
            while col_idx in pending and pending[col_idx] > 0:
                row[col_idx] = TableCell('', rowspan=0, colspan=0)
                pending[col_idx] -= 1
                if pending[col_idx] == 0:
                    del pending[col_idx]
                col_idx += 1

            rowspan = int(cell.get('rowspan', '1'))
            colspan = int(cell.get('colspan', '1'))
            text = get_rich_text(cell)

            row[col_idx] = TableCell(text, rowspan, colspan, is_tex=True)

            # 标记 rowspan
            if rowspan > 1:
                for dc in range(colspan):
                    pending[col_idx + dc] = rowspan - 1

            # 标记 colspan 占位格
            for dc in range(1, colspan):
                nc = col_idx + dc
                if nc < total_cols:
                    row[nc] = TableCell('', rowspan=0, colspan=0)

            col_idx += colspan

        # 尾部 pending 补占位符
        while col_idx in pending and pending[col_idx] > 0:
            row[col_idx] = TableCell('', rowspan=0, colspan=0)
            pending[col_idx] -= 1
            if pending[col_idx] == 0:
                del pending[col_idx]
            col_idx += 1

        grid.append(row)

    return {'type': 'table', 'rows': grid}


def _collect_table_rows(table_elem):
    """收集表格中的所有 <tr> 行（先 thead 再 tbody）。"""
    all_trs = []
    thead = table_elem.find('thead')
    if thead is not None:
        all_trs.extend(thead.findall('tr'))
    tbody = table_elem.find('tbody')
    if tbody is not None:
        all_trs.extend(tbody.findall('tr'))
    if not all_trs:
        all_trs = table_elem.findall('tr')
    return all_trs


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
            if child_text:
                parts.append(f'\\href{{{href}}}{{{child_text}}}')
        elif tag == 'latex':
            parts.append(parse_latex(child))
        elif tag == 'span':
            text_color = child.get('text-color', '')
            if text_color and not text_color.startswith('#'):
                # 仅支持命名的 xcolor 颜色，跳过 CSS 十六进制值
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
