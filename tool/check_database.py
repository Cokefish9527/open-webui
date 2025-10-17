#!/usr/bin/env python3
"""
直接检查数据库中的文件夹数据
"""

import sqlite3
import time

def check_database():
    """检查数据库中的文件夹数据"""
    print("=== 数据库文件夹数据检查 ===")
    
    # 数据库文件路径（根据你的配置调整）
    db_paths = [
        "c:/work/open-webui/backend/data/webui.db",
        "./data/webui.db",
        "../data/webui.db",
        "data/webui.db"
    ]
    
    db_path = None
    for path in db_paths:
        try:
            conn = sqlite3.connect(path)
            conn.close()
            db_path = path
            print(f"✅ 找到数据库: {path}")
            break
        except:
            continue
    
    if not db_path:
        print("❌ 无法找到数据库文件")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_material_folders'
        """)
        
        if not cursor.fetchone():
            print("❌ hsai_material_folders 表不存在")
            return False
        
        print("✅ hsai_material_folders 表存在")
        
        # 查看表结构
        cursor.execute("PRAGMA table_info(hsai_material_folders)")
        columns = cursor.fetchall()
        print("\n📋 表结构:")
        for col in columns:
            print(f"   {col[1]} ({col[2]}) - NULL: {not col[3]}")
        
        # 查询最近创建的文件夹
        print("\n📊 最近创建的文件夹 (最近10个):")
        cursor.execute("""
            SELECT id, name, parent_id, user_id, created_at 
            FROM hsai_material_folders 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        recent_folders = cursor.fetchall()
        for folder in recent_folders:
            parent_info = f"父目录: {folder[2]}" if folder[2] else "根目录"
            print(f"   {folder[1]} (ID: {folder[0]}) - {parent_info}")
        
        # 统计根目录和子目录数量
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id IS NULL")
        root_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id IS NOT NULL")
        child_count = cursor.fetchone()[0]
        
        print(f"\n📈 统计:")
        print(f"   根目录数量: {root_count}")
        print(f"   子目录数量: {child_count}")
        
        # 查找有子目录的根目录
        cursor.execute("""
            SELECT p.id, p.name, COUNT(c.id) as child_count
            FROM hsai_material_folders p
            LEFT JOIN hsai_material_folders c ON p.id = c.parent_id
            WHERE p.parent_id IS NULL
            GROUP BY p.id, p.name
            HAVING child_count > 0
            ORDER BY child_count DESC
            LIMIT 5
        """)
        
        parents_with_children = cursor.fetchall()
        print(f"\n👥 有子目录的根目录 (前5个):")
        for parent in parents_with_children:
            print(f"   {parent[1]} (ID: {parent[0]}) - {parent[2]} 个子目录")
        
        # 检查是否有孤儿文件夹（parent_id指向不存在的父目录）
        cursor.execute("""
            SELECT c.id, c.name, c.parent_id
            FROM hsai_material_folders c
            LEFT JOIN hsai_material_folders p ON c.parent_id = p.id
            WHERE c.parent_id IS NOT NULL AND p.id IS NULL
        """)
        
        orphaned = cursor.fetchall()
        if orphaned:
            print(f"\n⚠️  孤儿文件夹 (parent_id指向不存在的父目录):")
            for orphan in orphaned:
                print(f"   {orphan[1]} (ID: {orphan[0]}) - 父目录ID: {orphan[2]}")
        else:
            print(f"\n✅ 没有孤儿文件夹")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {str(e)}")
        return False

if __name__ == "__main__":
    check_database()