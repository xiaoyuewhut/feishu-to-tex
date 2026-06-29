"""公式块处理模块"""

import re


def parse_latex(latex_elem):
    """解析 latex 标签，返回处理后的 LaTeX 内容"""
    latex_content = latex_elem.text or ''
    # 去掉 <br/> 标签
    latex_content = latex_content.replace('<br/>', '').replace('<br>', '')
    # 把中文字符用 \text{} 包裹
    latex_content = wrap_chinese_in_text(latex_content)
    return f'${latex_content}$'


def wrap_chinese_in_text(content):
    """把中文字符用 \text{} 包裹（跳过已包裹的）"""
    # 先保护已有的 \text{...}，避免嵌套
    protected = []
    def _protect(m):
        protected.append(m.group(1))
        return f'\x00TEXT{len(protected) - 1}\x00'
    content = re.sub(r'\\text\{[^}]*\}', _protect, content)
    # 包裹剩余的中文字符
    content = re.sub(
        r'([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+)',
        r'\\text{\1}',
        content
    )
    # 还原已有的 \text{}
    for i, text in enumerate(protected):
        content = content.replace(f'\x00TEXT{i}\x00', f'\\text{{{text}}}')
    return content
