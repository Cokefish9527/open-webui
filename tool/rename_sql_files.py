#!/usr/bin/env python3
"""
脚本用于重新命名 SQL 文件，将日期部分移到文件名开头
原始格式: table_operation_YYYY-MM-DD.sql
目标格式: YYYY-MM-DD_table_operation.sql
"""

import os
import re
from pathlib import Path

def rename_sql_files(directory):
    """
    遍历指定目录中的 SQL 文件并重命名
    """
    # 匹配原始命名格式的正则表达式
    # 例如: hsai_tasks_alter_2025-10-05.sql 或 hsai_companies_create_2025-10-07.sql
    pattern = re.compile(r'^(.+?)_(\d{4}-\d{2}-\d{2})\.sql$')
    
    renamed_count = 0
    
    # 遍历目录中的所有文件
    for file_path in Path(directory).iterdir():
        if file_path.is_file() and file_path.suffix == '.sql':
            filename = file_path.name
            print(f"处理文件: {filename}")
            
            # 检查是否匹配原始命名模式
            match = pattern.match(filename)
            if match:
                table_operation = match.group(1)  # 表名+操作部分
                date_part = match.group(2)         # 日期部分
                
                # 构造新的文件名
                new_filename = f"{date_part}_{table_operation}.sql"
                new_file_path = file_path.parent / new_filename
                
                # 重命名文件
                try:
                    file_path.rename(new_file_path)
                    print(f"已重命名: {filename} -> {new_filename}")
                    renamed_count += 1
                except Exception as e:
                    print(f"重命名失败 {filename}: {e}")
            else:
                print(f"跳过文件（不符合命名规则）: {filename}")
    
    print(f"\n总共重命名了 {renamed_count} 个文件")

if __name__ == "__main__":
    # 定义要处理的目录
    directories = [
        "sql/schema_updates",
        "sql/init_scripts"
    ]
    
    # 获取脚本所在目录的父目录（backend目录）
    base_path = Path(__file__).parent.absolute()
    print(f"基础路径: {base_path}")
    
    for dir_name in directories:
        directory_path = base_path / dir_name
        print(f"尝试访问目录: {directory_path}")
        if directory_path.exists():
            print(f"正在处理目录: {directory_path}")
            rename_sql_files(directory_path)
            print("-" * 50)
        else:
            print(f"目录不存在: {directory_path}")