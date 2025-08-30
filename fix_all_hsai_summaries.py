#!/usr/bin/env python3
"""
修复所有HSAI相关API的Swagger注释
1. 添加中文summary
2. 简化docstring
"""

import re
import os
from pathlib import Path

# 定义接口名称映射
API_SUMMARIES = {
    # hsai_tasks.py
    'get_tasks': '获取任务列表',
    'create_task': '创建任务',
    'get_task': '获取任务详情',
    'update_task': '更新任务',
    'start_task': '启动任务',
    'cancel_task': '取消任务',
    'update_task_progress': '更新任务进度',
    'get_chat_cards': '获取聊天卡片',
    'create_card': '创建卡片',
    'update_card': '更新卡片',
    'get_task_stats': '获取任务统计',
    
    # hsai_matrix.py
    'get_platform_accounts': '获取平台账号',
    'create_platform_account': '创建平台账号',
    'update_account_token': '更新账号令牌',
    'update_account_stats': '更新账号统计',
    'sync_account_data': '同步账号数据',
    'get_account_groups': '获取账号分组',
    'create_account_group': '创建账号分组',
    'get_publish_tasks': '获取发布任务',
    'create_publish_task': '创建发布任务',
    'execute_publish_task': '执行发布任务',
    'update_publish_task_status': '更新发布任务状态',
    'get_oauth_url': '获取OAuth授权链接',
    'oauth_callback': 'OAuth回调处理',
    'get_publish_stats': '获取发布统计',
    'get_supported_platforms': '获取支持的平台',
    
    # hsai_ai.py
    'generate_video_script': '生成视频脚本',
    'analyze_product': '分析产品',
    'optimize_material': '优化素材',
    'generate_content_ideas': '生成内容创意',
    'chat': 'AI对话',
    'get_task_templates': '获取任务模板',
    
    # hsai_materials.py (已处理，但确保完整)
    'get_material_folders': '获取素材文件夹',
    'create_material_folder': '创建素材文件夹',
    'update_material_folder': '更新素材文件夹',
    'delete_material_folder': '删除素材文件夹',
    'get_materials': '获取素材列表',
    'search_materials': '搜索素材',
    'upload_material': '上传素材',
    'download_material': '下载素材',
    'get_material_thumbnail': '获取素材缩略图',
    'update_material': '更新素材信息',
    'delete_material': '删除素材',
    'get_material_stats': '获取素材统计',
}

def fix_router_decorators(content, filename):
    """修复路由装饰器，添加summary参数"""
    
    # 匹配各种形式的路由装饰器
    patterns = [
        # 单行装饰器: @router.get("/path", response_model=Model)
        r'(@router\.(get|post|put|delete)\([^)]+)\)\s*\n(async def (\w+)\()',
        # 多行装饰器: @router.post(\n    "/path",\n    response_model=Model\n)
        r'(@router\.(get|post|put|delete)\(\s*\n[^)]+)\)\s*\n(async def (\w+)\()',
    ]
    
    def replace_decorator(match):
        decorator = match.group(1)
        method = match.group(2)
        func_def = match.group(3)
        func_name = match.group(4)
        
        # 获取中文摘要
        summary = API_SUMMARIES.get(func_name, func_name)
        
        # 检查是否已经有summary参数
        if 'summary=' not in decorator:
            # 添加summary参数
            if decorator.strip().endswith(','):
                decorator = decorator + f' summary="{summary}"'
            else:
                decorator = decorator + f', summary="{summary}"'
        
        return f'{decorator})\n{func_def}'
    
    # 应用所有模式
    for pattern in patterns:
        content = re.sub(pattern, replace_decorator, content, flags=re.MULTILINE | re.DOTALL)
    
    return content

def simplify_docstrings(content):
    """简化docstring，去掉Args、Returns、Raises"""
    
    # 匹配函数的docstring
    pattern = r'(async def \w+\([^)]*\):\s*\n\s*""")(.*?)(""")'
    
    def simplify_docstring(match):
        prefix = match.group(1)
        docstring_content = match.group(2)
        suffix = match.group(3)
        
        # 分割成行
        lines = docstring_content.split('\n')
        
        # 找到第一个非空的描述行
        description_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(('Args:', 'Returns:', 'Raises:', 'Parameters:', 'Note:')):
                break
            description_lines.append(line)
        
        # 如果没有找到描述，使用函数名
        if not description_lines:
            description_lines = ['处理请求。']
        
        # 重新构建简化的docstring
        simplified = '\n    ' + '\n    '.join(description_lines) + '\n    '
        
        return f'{prefix}{simplified}{suffix}'
    
    return re.sub(pattern, simplify_docstring, content, flags=re.MULTILINE | re.DOTALL)

def process_file(file_path):
    """处理单个文件"""
    print(f"Processing {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修复路由装饰器
        content = fix_router_decorators(content, file_path.name)
        
        # 简化docstring
        content = simplify_docstrings(content)
        
        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated {file_path}")
        else:
            print(f"- No changes needed for {file_path}")
            
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")

def main():
    """主函数"""
    # 获取backend/open_webui/routers目录
    routers_dir = Path("backend/open_webui/routers")
    
    if not routers_dir.exists():
        print(f"Directory {routers_dir} not found")
        return
    
    # 处理所有HSAI相关的路由文件
    hsai_files = list(routers_dir.glob("hsai_*.py"))
    
    if not hsai_files:
        print("No HSAI router files found")
        return
    
    print(f"Found {len(hsai_files)} HSAI router files:")
    for file_path in hsai_files:
        print(f"  - {file_path}")
    
    print("\nProcessing files...")
    for file_path in hsai_files:
        process_file(file_path)
    
    print("\nDone!")

if __name__ == "__main__":
    main()