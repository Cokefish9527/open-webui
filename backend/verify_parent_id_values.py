#!/usr/bin/env python3
"""
验证数据库中parent_id字段的实际值
"""

import sqlite3
import time

def check_parent_id_values():
    """检查parent_id字段的各种可能值"""
    print("=== 检查parent_id字段值类型 ===")
    
    # 数据库文件路径
    db_path = "c:/work/open-webui/backend/data/webui.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查parent_id的所有不同值
        print("📊 parent_id字段的所有不同值:")
        cursor.execute("""
            SELECT DISTINCT parent_id, COUNT(*) as count
            FROM hsai_material_folders 
            GROUP BY parent_id
            ORDER BY count DESC
        """)
        
        distinct_values = cursor.fetchall()
        for value, count in distinct_values[:20]:  # 显示前20个
            if value is None:
                print(f"   NULL: {count} 个文件夹")
            elif value == "":
                print(f"   空字符串 '': {count} 个文件夹")
            elif len(str(value)) == 0:
                print(f"   长度为0的值: {count} 个文件夹")
            else:
                print(f"   '{value}': {count} 个文件夹")
        
        print(f"\n📋 parent_id值的统计:")
        
        # 统计NULL值
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"   IS NULL: {null_count}")
        
        # 统计空字符串
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id = ''")
        empty_string_count = cursor.fetchone()[0]
        print(f"   = '': {empty_string_count}")
        
        # 统计非空非NULL值
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id IS NOT NULL AND parent_id != ''")
        valid_parent_count = cursor.fetchone()[0]
        print(f"   有效parent_id: {valid_parent_count}")
        
        # 检查最近创建的几个文件夹
        print(f"\n🔍 最近创建的子文件夹详情:")
        cursor.execute("""
            SELECT id, name, parent_id, LENGTH(parent_id) as parent_id_length, 
                   CASE 
                       WHEN parent_id IS NULL THEN 'NULL'
                       WHEN parent_id = '' THEN 'EMPTY_STRING'
                       ELSE 'VALID'
                   END as parent_id_type
            FROM hsai_material_folders 
            WHERE parent_id IS NOT NULL AND parent_id != ''
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        recent_children = cursor.fetchall()
        for folder in recent_children:
            print(f"   {folder[1]} (ID: {folder[0]})")
            print(f"     parent_id: '{folder[2]}' (长度: {folder[3]}, 类型: {folder[4]})")
        
        # 特别检查最近的debug文件夹
        print(f"\n🎯 检查最近的debug文件夹:")
        cursor.execute("""
            SELECT id, name, parent_id, created_at
            FROM hsai_material_folders 
            WHERE name LIKE 'debug_%'
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        debug_folders = cursor.fetchall()
        for folder in debug_folders:
            print(f"   {folder[1]} (ID: {folder[0]}) - parent_id: {repr(folder[2])}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        return False

if __name__ == "__main__":
    check_parent_id_values()