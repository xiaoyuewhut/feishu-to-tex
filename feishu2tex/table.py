"""表格生成模块"""

from .utils import escape_tex


def calc_col_widths(rows, cols):
    """根据内容计算每列宽度比例"""
    # 使用更精确的宽度计算：中文字符算2个宽度，其他算1个
    def char_width(ch):
        if '\u4e00' <= ch <= '\u9fff':
            return 2  # 中文字符
        return 1
    
    def text_width(text):
        return sum(char_width(ch) for ch in str(text))
    
    col_total_width = [0] * cols
    col_max_width = [0] * cols
    col_counts = [0] * cols
    
    for row in rows:
        for i, cell in enumerate(row):
            if i < cols:
                w = text_width(cell)
                col_total_width[i] += w
                col_max_width[i] = max(col_max_width[i], w)
                if w > 0:
                    col_counts[i] += 1
    
    # 计算每列的平均宽度
    col_avg_width = []
    for i in range(cols):
        if col_counts[i] > 0:
            col_avg_width.append(col_total_width[i] / col_counts[i])
        else:
            col_avg_width.append(2)  # 默认最小宽度
    
    # 根据平均宽度计算列宽比例
    total_avg = sum(col_avg_width)
    col_widths = [(avg / total_avg) * 0.92 for avg in col_avg_width]
    
    # 确保最小列宽（至少占总宽度的8%）
    min_width = 0.08
    col_widths = [max(w, min_width) for w in col_widths]
    
    # 归一化
    total_width = sum(col_widths)
    col_widths = [w / total_width for w in col_widths]
    
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
    
    # 计算合并信息
    merge_info = calc_merge_info(rows, cols)
    
    # 判断是否使用 longtable（超过 20 行）
    use_longtable = len(rows) > 20
    
    # 使用 M{} 类型实现垂直居中 + 允许换行 + 居中对齐
    col_specs = [f'M{{{w:.3f}\\textwidth}}' for w in col_widths]
    col_spec = ''.join(col_specs)
    
    if use_longtable:
        lines.append('\\begin{longtable}{' + col_spec + '}')
        lines.append('  \\toprule')
        # 表头
        header_cells = [f'\\textbf{{{escape_tex(str(cell))}}}' for cell in rows[0]]
        lines.append(f'  {" & ".join(header_cells)} \\\\')
        lines.append('  \\midrule')
        lines.append('  \\endfirsthead')
        # 续表表头
        lines.append('  \\toprule')
        lines.append(f'  {" & ".join(header_cells)} \\\\')
        lines.append('  \\midrule')
        lines.append('  \\endhead')
        # 续表表尾
        lines.append('  \\midrule')
        lines.append('  \\multicolumn{' + str(cols) + '}{r}{\\textit{续下页}} \\\\')
        lines.append('  \\endfoot')
        # 最后一页表尾
        lines.append('  \\bottomrule')
        lines.append('  \\endlastfoot')
    else:
        lines.append('\\begin{table}[htbp]')
        lines.append('  \\centering')
        lines.append('  \\small')
        lines.append('  \\renewcommand{\\arraystretch}{1.4}')
        lines.append(f'  \\begin{{tabular}}{{{col_spec}}}')
        lines.append('    \\toprule')
    
    # 生成表格行
    start_row = 1 if use_longtable else 1
    for r in range(start_row, len(rows)):
        row = rows[r]
        cells = []
        
        for c in range(cols):
            info = merge_info[r][c]
            if info is None:
                cells.append('')
            elif info[0] == 0:
                # 被合并的单元格
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
            indent = '  ' if use_longtable else '    '
            lines.append(f'{indent}{" & ".join(cells)} \\\\')
    
    if use_longtable:
        lines.append('\\end{longtable}')
    else:
        lines.append('    \\bottomrule')
        lines.append('  \\end{tabular}')
        lines.append('\\end{table}')
    
    lines.append('')
    
    return '\n'.join(lines)
