"""工具函数"""

import os
import re
from urllib.parse import urlparse


def strip_heading_number(text):
    """去掉标题开头的数字序号（作用于原始文本）。"""
    return _strip_heading_raw(text)[1]


def strip_heading_tex(raw_text, tex_text):
    """从标题的 raw 和 tex 两端去掉数字序号，返回可用于 LaTeX 输出的文本。

    先对 raw_text 做 strip，再将对应的序号前缀从 tex_text 移除。
    若 tex_text 中找不到序号（比如序号被 LaTeX 命令包裹），则回退到
    直接对 tex_text 做正则 strip。
    """
    prefix, raw_suffix = _strip_heading_raw(raw_text)
    if not prefix:
        return tex_text

    # 在 tex_text 中查找并移除同样的前缀
    idx = tex_text.find(prefix)
    if idx >= 0:
        end = idx + len(prefix)
        if end < len(tex_text) and tex_text[end] == ' ':
            end += 1
        stripped = (tex_text[:idx] + tex_text[end:]).strip()
        # 如果 tex 前缀被移除后为空，保留后缀
        if stripped:
            return stripped

    # 回退：直接对 tex_text 做正则 strip
    return strip_heading_number(tex_text)


def _strip_heading_raw(text):
    """去掉标题开头的数字序号。
    返回 (prefix, suffix)，若无需 strip 则 prefix 为 None。
    """
    m = re.match(r'^([\d]+(\.[\d]+)*\.?)\s*(?![xX\d])', text)
    if m and m.group(1):
        suffix = text[m.end():].strip()
        if not suffix:
            return m.group(1).rstrip('.'), ''
        return m.group(1), suffix
    return None, text


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


def is_svg_file(filepath):
    """检测文件是否为 SVG（按扩展名或文件头）。"""
    if filepath.lower().endswith('.svg'):
        return True
    try:
        with open(filepath, 'rb') as f:
            head = f.read(200).decode('utf-8', errors='ignore')
            return '<svg' in head.lower() or '<!doctype svg' in head.lower()
    except Exception:
        return False


def convert_svg_to_png(svg_path):
    """将 SVG 转换为 PNG，返回 PNG 路径或 None。

    优先使用 macOS qlmanage，其次尝试 rsvg-convert / inkscape。
    """
    png_path = svg_path + '.png'

    # 尝试 qlmanage (macOS)
    try:
        import subprocess
        result = subprocess.run(
            ['qlmanage', '-t', '-s', '1200', '-o',
             os.path.dirname(svg_path), svg_path],
            capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(png_path):
            return png_path
    except Exception:
        pass

    # 尝试 rsvg-convert
    try:
        import subprocess
        result = subprocess.run(
            ['rsvg-convert', '-w', '1200', '-o', png_path, svg_path],
            capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(png_path):
            return png_path
    except Exception:
        pass

    # 尝试 inkscape
    try:
        import subprocess
        result = subprocess.run(
            ['inkscape', '--export-type=png', '--export-width=1200',
             f'--export-filename={png_path}', svg_path],
            capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(png_path):
            return png_path
    except Exception:
        pass

    return None
