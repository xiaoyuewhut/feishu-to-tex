"""高亮块（Callout）解析与生成"""

from .utils import escape_tex


def parse_callout(elem):
    """解析 callout XML 元素为块"""
    from .feishu import get_rich_text
    icon = elem.get('icon', '')
    content = get_rich_text(elem)
    return {'type': 'callout', 'content': content, 'icon': icon}


def generate_callout_tex(block):
    """生成 callout 的 LaTeX 代码"""
    lines = []
    icon = escape_tex(block.get('icon', ''))
    content = block['content']
    if icon:
        lines.append(f'\\begin{{calloutbox}}{{{icon}}}')
    else:
        lines.append('\\begin{calloutbox}{}')
    lines.append(content)
    lines.append('\\end{calloutbox}')
    lines.append('')
    return lines


def generate_callout_style():
    """生成 callout 的 LaTeX 样式定义"""
    return r"""% 高亮块（callout）样式
\newtcolorbox{calloutbox}[1]{
  colback=blue!5!white,
  colframe=blue!50!black,
  fonttitle=\bfseries,
  title={#1},
  boxrule=0.5pt,
  arc=2pt,
  left=8pt,
  right=8pt,
  top=6pt,
  bottom=6pt,
}
"""
