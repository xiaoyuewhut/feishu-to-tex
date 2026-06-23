"""表格生成模块"""

import math
from .utils import escape_tex


def calc_col_widths(rows, cols):
    """根据内容计算每列宽度比例（稳健宽度算法）"""
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
        return [1.0]
    
    # 收集每列的宽度数据
    col_widths = []
    for c in range(cols):
        header_w = 0
        content_widths = []
        for r in range(len(rows)):
            w = text_width(rows[r][c]) if c < len(rows[r]) else 0
            if r == 0:
                header_w = w
            else:
                content_widths.append(w)
        
        # 用 max(表头宽度, 内容80分位宽度) 作为该列宽度
        if content_widths:
            content_widths.sort()
            idx = int(len(content_widths) * 0.8)
            p80 = content_widths[min(idx, len(content_widths) - 1)]
        else:
            p80 = 0
        
        col_widths.append(max(header_w, p80, 1))
    
    # 设置上下限
    MIN_WIDTH = 0.07
    MAX_WIDTH = 0.28
    
    # 根据列数决定可用总宽度（预留 tabcolsep + 竖线空间）
    if cols <= 4:
        avail = 0.92
    elif cols <= 8:
        avail = 0.88
    elif cols <= 12:
        avail = 0.84
    else:
        avail = 0.80
    
    # 归一化到可用宽度
    total = sum(col_widths)
    col_widths = [(w / total) * avail for w in col_widths]
    
    # 应用上下限
    col_widths = [max(MIN_WIDTH, min(MAX_WIDTH, w)) for w in col_widths]
    
    # 再次归一化
    total = sum(col_widths)
    col_widths = [(w / total) * avail for w in col_widths]
    
    return col_widths


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
    """生成表格的 LaTeX 代码"""
    if not rows:
        return ''
    
    lines = []
    cols = max(len(row) for row in rows)
    
    # 计算列宽
    col_widths = calc_col_widths(rows, cols)
    col_spec = ''.join([f'p{{{w:.3f}\\textwidth}}' for w in col_widths])
    
    # 计算合并信息
    merge_info = calc_merge_info(rows, cols)
    
    # 使用 longtable，去掉竖线，局部设置 tabcolsep
    lines.append('\\small')
    lines.append('\\setlength{\\tabcolsep}{3pt}')
    lines.append('\\renewcommand{\\arraystretch}{1.4}')
    lines.append('\\begin{longtable}{' + col_spec + '}')
    lines.append('  \\toprule')
    header_cells = [f'\\textbf{{{escape_tex(str(cell))}}}' for cell in rows[0]]
    lines.append(f'  {" & ".join(header_cells)} \\\\')
    lines.append('  \\midrule')
    lines.append('  \\endfirsthead')
    lines.append('  \\toprule')
    lines.append(f'  {" & ".join(header_cells)} \\\\')
    lines.append('  \\midrule')
    lines.append('  \\endhead')
    lines.append('  \\midrule')
    lines.append(f'  \\multicolumn{{{cols}}}{{r}}{{\\textit{{续下页}}}} \\\\')
    lines.append('  \\endfoot')
    lines.append('  \\bottomrule')
    lines.append('  \\endlastfoot')
    
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
                width = col_widths[c]
                cells.append(f'\\multirow{{{info[0]}}}{{{width:.3f}\\textwidth}}{{{escape_tex(info[1])}}}')
            else:
                cells.append(escape_tex(info[1]))
        lines.append(f'  {" & ".join(cells)} \\\\')
    
    lines.append('\\end{longtable}')
    lines.append('')
    
    return '\n'.join(lines)
