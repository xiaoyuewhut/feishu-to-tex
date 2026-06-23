"""项目生成"""

import os
import json
from datetime import datetime

from .utils import (
    sanitize_filename, sanitize_ascii, to_folder_name,
    strip_heading_number, download_image, guess_image_ext
)
from .tex import (
    generate_tex, generate_main_tex, generate_style_file,
    generate_latexmkrc, split_sections
)


def create_project(blocks, title, doc_id, output_dir):
    """创建 LaTeX 项目"""
    # 生成文件夹名
    folder_name = to_folder_name(title, doc_id)
    project_dir = os.path.join(output_dir, folder_name)
    
    # 创建目录结构
    os.makedirs(os.path.join(project_dir, 'sections'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'assets', 'images'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'styles'), exist_ok=True)
    
    # 下载图片
    image_map = {}
    image_idx = 0
    warnings = []
    
    for block in blocks:
        if block.get('type') == 'image' and block.get('src'):
            image_idx += 1
            num = str(image_idx).zfill(3)
            ext = guess_image_ext(block['src'])
            filename = f'image-{num}{ext}'
            filepath = os.path.join(project_dir, 'assets', 'images', filename)
            
            if download_image(block['src'], filepath):
                image_map[block['src']] = f'assets/images/{filename}'
            else:
                warnings.append(f'图片下载失败: {block["src"]}')
                image_map[block['src']] = None
    
    # 替换图片引用
    for block in blocks:
        if block.get('type') == 'image' and block.get('src'):
            local_path = image_map.get(block['src'])
            if local_path:
                block['local_path'] = local_path
    
    # 分章节
    sections = split_sections(blocks)
    
    # 生成 main.tex
    main_tex = generate_main_tex(title, sections)
    with open(os.path.join(project_dir, 'main.tex'), 'w', encoding='utf-8') as f:
        f.write(main_tex)
    
    # 生成各章节
    for i, section in enumerate(sections):
        num = str(i + 1).zfill(2)
        heading = section.get('heading')
        # 去掉标题中的序号，用于文件名
        clean_heading = strip_heading_number(heading) if heading else None
        name = sanitize_ascii(clean_heading or 'content')
        filename = f'{num}-{name}.tex'
        
        section_tex = generate_tex(section.get('blocks', []))
        with open(os.path.join(project_dir, 'sections', filename), 'w', encoding='utf-8') as f:
            f.write(section_tex)
    
    # 生成样式文件
    with open(os.path.join(project_dir, 'styles', 'feishu.sty'), 'w', encoding='utf-8') as f:
        f.write(generate_style_file())
    
    # 生成 latexmkrc
    with open(os.path.join(project_dir, 'latexmkrc'), 'w', encoding='utf-8') as f:
        f.write(generate_latexmkrc())
    
    # 生成 metadata.json
    metadata = {
        'title': title,
        'doc_id': doc_id,
        'exported_at': datetime.now().isoformat(),
        'block_count': len(blocks),
        'section_count': len(sections),
        'image_count': image_idx,
    }
    with open(os.path.join(project_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # 生成 conversion-report.json
    report = {
        'title': title,
        'doc_id': doc_id,
        'timestamp': datetime.now().isoformat(),
        'total_blocks': len(blocks),
        'total_sections': len(sections),
        'total_images': image_idx,
        'downloaded_images': image_idx - len(warnings),
        'sections': [
            {
                'file': f'sections/{str(i + 1).zfill(2)}-{sanitize_ascii(strip_heading_number(section.get("heading")) if section.get("heading") else "content")}.tex',
                'blocks': len(section.get('blocks', []))
            }
            for i, section in enumerate(sections)
        ],
        'warnings': warnings
    }
    with open(os.path.join(project_dir, 'conversion-report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return project_dir, folder_name
