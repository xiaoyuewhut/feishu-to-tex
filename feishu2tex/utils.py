"""工具函数"""

import os
import re
from urllib.parse import urlparse


def strip_heading_number(text):
    """去掉标题开头的数字序号，如 '1.1 xxx' -> 'xxx', '2.' -> '2'"""
    # 匹配开头的数字序号: 1. / 1.1 / 1.1.1 / 1.1.1.1 等
    # 排除十六进制数（如 0x27）和版本号（如 v2.0）
    m = re.match(r'^([\d]+(\.[\d]+)*\.?)\s*(?![xX\d])', text)
    if m and m.group(1):
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
    # 处理特殊符号
    text = text.replace('★', '$\\bigstar$')
    text = text.replace('☆', '$\\bigstar$')
    text = text.replace('●', '$\\bullet$')
    text = text.replace('○', '$\\circ$')
    text = text.replace('■', '$\\blacksquare$')
    text = text.replace('□', '$\\square$')
    text = text.replace('▲', '$\\blacktriangle$')
    text = text.replace('△', '$\\triangle$')
    text = text.replace('◆', '$\\blacklozenge$')
    text = text.replace('◇', '$\\lozenge$')
    text = text.replace('→', '$\\rightarrow$')
    text = text.replace('←', '$\\leftarrow$')
    text = text.replace('↑', '$\\uparrow$')
    text = text.replace('↓', '$\\downarrow$')
    text = text.replace('↔', '$\\leftrightarrow$')
    text = text.replace('⇒', '$\\Rightarrow$')
    text = text.replace('⇐', '$\\Leftarrow$')
    text = text.replace('⇔', '$\\Leftrightarrow$')
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
    # 用 os.path.splitext 提取真正的扩展名
    ext = os.path.splitext(path)[1]
    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'):
        return '.jpg' if ext == '.jpeg' else ext
    return '.png'
