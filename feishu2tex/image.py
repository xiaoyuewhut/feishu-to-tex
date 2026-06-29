"""图片解析与 LaTeX 生成"""

import re

from .utils import escape_tex


def generate_image_tex(local_path, alt, image_index):
    """生成图片的 LaTeX 代码（参照表格的 minipage + adjustbox 方式）
    
    Args:
        local_path: 图片本地路径
        alt: 图片 alt 文本（可能为空或占位）
        image_index: 图片序号（用于 label）
    
    Returns:
        list: LaTeX 代码行列表
    """
    lines = []
    
    # 参照表格处理方式：minipage + adjustbox，固定在当前位置
    # 有真实 caption 时留出更多空间
    has_caption = alt and not re.match(
        r'^(paste|image|img|图片|截图|Pasted image).*$', alt, re.IGNORECASE
    )
    # max_height：图片可伸缩上限，有 caption 时稍小以容纳标题
    max_height = '0.55\\textheight' if has_caption else '0.6\\textheight'
    # needspace：如果当前剩余空间连缩小阈值都达不到，则换页
    lines.append(f'\\needspace{{0.3\\textheight}}')
    lines.append('\\vspace{0.5em}')
    lines.append('\\noindent\\begin{minipage}{\\linewidth}')
    lines.append('  \\centering')
    lines.append(f'  \\begin{{adjustbox}}{{max width=\\textwidth, max height={max_height}, keepaspectratio}}')
    lines.append(f'  \\includegraphics{{{local_path}}}')
    lines.append(f'  \\end{{adjustbox}}')
    lines.append(f'  \\par')
    if has_caption:
        lines.append(f'  \\refstepcounter{{figure}}\\label{{fig:img-{image_index}}}')
        lines.append(f'  {{\\centering\\small\\figurename\\ \\thefigure: {escape_tex(alt)}\\par}}')
    else:
        lines.append('  \\refstepcounter{figure}')
        lines.append(f'  \\label{{fig:img-{image_index}}}')
        lines.append(f'  {{\\centering\\small\\figurename\\ \\thefigure\\par}}')
    lines.append('\\end{minipage}')
    lines.append('\\vspace{0.5em}')
    
    return lines
