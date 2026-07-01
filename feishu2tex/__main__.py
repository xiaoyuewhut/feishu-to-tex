#!/usr/bin/env python3
"""
飞书文档转 LaTeX CLI 工具
用法: python3 -m feishu2tex <飞书文档URL> [输出目录]
"""

import sys
import os

from .feishu import run_lark_cli, extract_doc_info, parse_xml_content
from .project import create_project


def main():
    if len(sys.argv) < 2:
        print('用法: python3 -m feishu2tex <飞书文档URL> [输出目录]')
        print('')
        print('示例:')
        print('  python3 -m feishu2tex https://xxx.feishu.cn/docx/Z1Fj...tnAc')
        print('  python3 -m feishu2tex https://xxx.feishu.cn/wiki/xxx ./test')
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    print(f'正在获取文档: {url}')
    
    try:
        # 调用 lark-cli
        response = run_lark_cli(url)
        doc_id, content = extract_doc_info(response)
        
        print(f'文档 ID: {doc_id}')
        print(f'内容长度: {len(content)} 字符')
        
        # 解析 XML
        blocks = parse_xml_content(content)
        print(f'解析到 {len(blocks)} 个内容块')
        
        if not blocks:
            print('错误: 未能解析到任何内容')
            sys.exit(1)
        
        # 获取标题
        title = 'untitled'
        for block in blocks:
            if block.get('type') == 'title':
                title = block.get('content', 'untitled')
                break
            elif block.get('type') == 'heading' and block.get('level') == 1:
                title = block.get('raw_content', block.get('content', 'untitled'))
                break
        
        print(f'文档标题: {title}')
        
        # 创建项目
        print('正在生成 LaTeX 项目...')
        project_dir, folder_name = create_project(blocks, title, doc_id, output_dir, source_url=url)
        
        print(f'\n✓ 完成!')
        print(f'  项目目录: {project_dir}')
        print(f'\n上传 {project_dir} 到 Overleaf 即可编译')
        
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
