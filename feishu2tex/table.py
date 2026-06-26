"""表格生成模块"""

from .utils import escape_tex


ROWSPAN_PAGEBREAK_THRESHOLD = 6
MIN_ROWS_FOR_ROWSPAN_PAGEBREAK = 24


def cell_text(row, col):
    """取单元格文本，越界视为空。"""
    if col >= len(row):
        return ''
    return str(row[col]).strip()


def calc_col_weights(rows, cols):
    """根据内容计算每列权重（用于 tabularray 的 X 列）"""
    def char_width(ch):
        if '\u4e00' <= ch <= '\u9fff':
            return 2  # 中文字符
        return 1
    
    def text_width(text):
        return sum(char_width(ch) for ch in str(text))
    
    # 裁掉全空尾列
    while cols > 0:
        last_col = cols - 1
        last_col_empty = all(
            (last_col >= len(rows[r]) or str(rows[r][last_col]).strip() == '')
            for r in range(len(rows))
        )
        if last_col_empty:
            cols -= 1
        else:
            break
    
    if cols == 0:
        return [1]
    
    # 收集每列的宽度数据
    col_weights = []
    for c in range(cols):
        header_w = 0
        content_widths = []
        for r in range(len(rows)):
            w = text_width(rows[r][c]) if c < len(rows[r]) else 0
            if r == 0:
                header_w = w
            else:
                content_widths.append(w)
        
        # 用 max(表头宽度, 内容最大宽度) 作为该列权重
        if content_widths:
            max_w = max(content_widths)
        else:
            max_w = 0
        
        col_weights.append(max(header_w, max_w, 1))
    
    # 归一化为整数权重（最小1）
    min_w = min(col_weights)
    col_weights = [max(1, round(w / min_w)) for w in col_weights]
    
    return col_weights


def trim_empty_tail_cols(rows):
    """裁掉全空尾列，避免 colspec 与实际列数不一致。"""
    cols = max(len(row) for row in rows)
    while cols > 0:
        last_col = cols - 1
        if all(cell_text(row, last_col) == '' for row in rows):
            cols -= 1
        else:
            break
    return max(cols, 1)


def calc_merge_info(rows, cols):
    """计算合并单元格信息"""
    merge_info = [[None for _ in range(cols)] for _ in range(len(rows))]
    
    def cell_val(r, c):
        if c >= len(rows[r]):
            return ''
        return str(rows[r][c]).strip()
    
    # 先计算每列的合并范围
    for c in range(cols):
        r = 0
        while r < len(rows):
            val = cell_val(r, c)
            if val == '':
                r += 1
                continue
            
            # 计算向下合并的行数
            span = 1
            while r + span < len(rows):
                if cell_val(r + span, c) == '':
                    span += 1
                else:
                    break
            
            if span > 1:
                merge_info[r][c] = (span, cell_val(r, c))
                for k in range(1, span):
                    merge_info[r + k][c] = (0, '')
            else:
                merge_info[r][c] = (1, val)
            
            r += span
    
    return merge_info


def row_starts_large_span(merge_info, row_index, cols):
    """判断当前行是否开始了较大的纵向合并块。"""
    for c in range(cols):
        info = merge_info[row_index][c]
        if info and info[0] >= ROWSPAN_PAGEBREAK_THRESHOLD:
            return True
    return False


def should_hint_rowspan_pagebreak(rows):
    """短表通常能整体放下，不需要给 rowspan 额外分页提示。"""
    return len(rows) >= MIN_ROWS_FOR_ROWSPAN_PAGEBREAK


def generate_table_tex(rows, caption=None):
    """生成表格的 LaTeX 代码"""
    if not rows:
        return ''
    
    lines = []
    cols = trim_empty_tail_cols(rows)
    
    # 计算列权重
    col_weights = calc_col_weights(rows, cols)
    colspec = ' '.join([f'X[{w},l]' for w in col_weights])
    
    # 计算合并信息
    merge_info = calc_merge_info(rows, cols)
    
    # 判断表格大小：考虑行数和内容长度
    SMALL_TABLE_MAX_ROWS = 25
    row_count = len(rows)
    
    # 计算内容总长度（用于判断是否需要跨页）
    total_content_length = 0
    for r in range(row_count):
        for c in range(cols):
            cell = str(rows[r][c]) if c < len(rows[r]) else ''
            total_content_length += len(cell)
    
    # 估算每行平均高度（中文字符约 2 个单位，其他 1 个单位）
    avg_chars_per_row = total_content_length / max(row_count - 1, 1)  # 减去表头
    
    # 判断是否需要跨页：
    # 1. 行数超过阈值
    # 2. 或者内容很长（平均每行超过 100 个字符）
    # 3. 或者有大量合并单元格（跨行合并超过 5 个）
    large_rowspan_count = 0
    for r in range(row_count):
        for c in range(cols):
            info = merge_info[r][c]
            if info and info[0] >= 5:
                large_rowspan_count += 1
    
    needs_pagebreak = (
        row_count > SMALL_TABLE_MAX_ROWS or
        avg_chars_per_row > 100 or
        large_rowspan_count > 8
    )
    
    lines.append('\\small')
    
    if not needs_pagebreak:
        # 小表：不使用浮动体，直接固定在当前位置
        # 使用 adjustbox 的 max height 让表格自适应页面空间
        # 根据行数动态调整缩放比例：行数越多缩放越激进
        if row_count <= 6:
            max_height = '0.7\\textheight'
        elif row_count <= 10:
            max_height = '0.55\\textheight'
        elif row_count <= 14:
            max_height = '0.4\\textheight'
        elif row_count <= 18:
            max_height = '0.3\\textheight'
        else:
            max_height = '0.25\\textheight'
        
        lines.append('\\vspace{0.5em}')
        lines.append('\\noindent\\begin{minipage}{\\linewidth}')
        lines.append('\\centering')
        if caption:
            lines.append(f'\\textbf{{{escape_tex(caption)}}}\\\\[0.5em]')
        lines.append(f'\\begin{{adjustbox}}{{max height={max_height}, center}}')
        lines.append(f'  \\begin{{tblr}}{{')
        lines.append(f'    width=\\linewidth,')
        lines.append(f'    colspec={{{colspec}}},')
        lines.append('    cells={valign=m},')
        lines.append('    hlines,')
        lines.append('    vlines,')
        lines.append('    hline{1,Z}={1pt},')
        lines.append('    row{1}={font=\\bfseries},')
        lines.append('  }')
    else:
        # 大表：用 longtblr 跨页
        lines.append('\\begin{longtblr}[')
        if caption:
            lines.append(f'  caption={{{escape_tex(caption)}}},')
        lines.append('  entry={none},')
        lines.append('  label={none},')
        lines.append(']{')
        lines.append(f'  width=\\linewidth,')
        lines.append(f'  colspec={{{colspec}}},')
        lines.append('  cells={valign=m},')
        lines.append('  rowhead=1,')
        lines.append('  hlines,')
        lines.append('  vlines,')
        lines.append('  hline{1,Z}={1pt},')
        lines.append('    row{1}={font=\\bfseries},')
        lines.append('}')
    
    # 表头
    header_cells = [escape_tex(str(cell)) for cell in rows[0]]
    lines.append(f'  {" & ".join(header_cells)} \\\\')
    
    # 数据行
    for r in range(1, len(rows)):
        row = rows[r]
        cells = []
        for c in range(cols):
            info = merge_info[r][c]
            if info is None:
                cells.append('')
            elif info[0] == 0:
                cells.append('')
            elif info[0] > 1:
                cells.append(f'\\SetCell[r={info[0]}]{{l}} {escape_tex(info[1])}')
            else:
                cells.append(escape_tex(info[1]))
        lines.append(f'  {" & ".join(cells)} \\\\')
    
    if not needs_pagebreak:
        lines.append('  \\end{tblr}')
        lines.append('  \\end{adjustbox}')
        lines.append('\\end{minipage}')
        lines.append('\\vspace{0.5em}')
    else:
        lines.append('\\end{longtblr}')
    
    lines.append('')
    
    return '\n'.join(lines)
