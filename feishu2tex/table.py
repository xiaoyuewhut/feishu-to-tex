"""表格生成模块"""

from .utils import escape_tex


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
        
        # 用 max(表头宽度, 内容80分位宽度) 作为该列权重
        if content_widths:
            content_widths.sort()
            idx = int(len(content_widths) * 0.8)
            p80 = content_widths[min(idx, len(content_widths) - 1)]
        else:
            p80 = 0
        
        col_weights.append(max(header_w, p80, 1))
    
    # 归一化为整数权重（最小1）
    min_w = min(col_weights)
    col_weights = [max(1, round(w / min_w)) for w in col_weights]
    
    return col_weights


def calc_merge_info(rows, cols):
    """计算合并单元格信息"""
    merge_info = [[None for _ in range(cols)] for _ in range(len(rows))]
    
    for c in range(cols):
        r = 0
        while r < len(rows):
            cell_val = str(rows[r][c]) if c < len(rows[r]) else ''
            if cell_val.strip() == '':
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
                    merge_info[r + k][c] = (0, '')
            else:
                merge_info[r][c] = (1, cell_val)
            r += span
    
    return merge_info


def generate_table_tex(rows):
    """生成表格的 LaTeX 代码（使用 tabularray 的 longtblr）"""
    if not rows:
        return ''
    
    lines = []
    cols = max(len(row) for row in rows)
    
    # 计算列权重
    col_weights = calc_col_weights(rows, cols)
    colspec = ' '.join([f'X[{w},l]' for w in col_weights])
    
    # 计算合并信息
    merge_info = calc_merge_info(rows, cols)
    
    # 使用 tabularray 的 longtblr
    lines.append('\\small')
    lines.append('\\begin{longtblr}[')
    lines.append('  entry={none},')
    lines.append('  label={none},')
    lines.append(']{')
    lines.append(f'  width=\\linewidth,')
    lines.append(f'  colspec={{{colspec}}},')
    lines.append('  rowhead=1,')
    lines.append('  hlines,')
    lines.append('  hline{1,Z}={1pt},')
    lines.append('  row{1}={font=\\bfseries},')
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
    
    lines.append('\\end{longtblr}')
    lines.append('')
    
    return '\n'.join(lines)
