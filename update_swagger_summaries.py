#!/usr/bin/env python3
"""
批量更新HSAI相关API的Swagger注释
1. 添加中文summary
2. 简化docstring，去掉Args、Returns、Raises
"""

import re
import os
from pathlib import Path

# 定义接口名称映射
API_SUMMARIES = {
    # hsai_materials.py
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
}

def update_router_file(file_path):
    """更新单个路由文件"""
    print(f"Processing {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配路由装饰器和函数定义
    pattern = r'(@router\.(get|post|put|delete)\([^)]+)\)\s*\nasync def (\w+)\([^)]*\):\s*\n\s*"""([^"]*?)"""'
    
    def replace_func(match):
        decorator = match.group(1)
        method = match.group(2)
        func_name = match.group(3)
        docstring = match.group(4).strip()
        
        # 获取中文摘要
        summary = API_SUMMARIES.get(func_name, func_name)
        
        # 检查是否已经有summary参数
        if 'summary=' not in decorator:
            # 添加summary参数
            if decorator.endswith(')'):
                decorator = decorator[:-1] + f', summary="{summary}")'
            else:
                decorator = decorator + f', summary="{summary}"'
        
        # 简化docstring - 只保留第一行描述
        lines = docstring.split('\n')
        simple_desc = lines[0].strip() if lines else summary
        
        # 如果第一行为空，尝试找到第一个非空行
        if not simple_desc:
            for line in lines:
                line = line.strip()
                if line and not line.startswith(('Args:', 'Returns:', 'Raises:')):
                    simple_desc = line
                    break
        
        if not simple_desc:
            simple_desc = summary
        
        return f'{decorator})\nasync def {func_name}({match.group(0).split("(", 1)[1].split("):", 1)[0]}):\n    """\n    {simple_desc}\n    """'
    
    # 执行替换
    new_content = re.sub(pattern, replace_func, content, flags=re.MULTILINE | re.DOTALL)
    
    # 写回文件
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")

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
    
    for file_path in hsai_files:
        try:
            update_router_file(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    main()