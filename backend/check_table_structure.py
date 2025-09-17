#!/usr/bin/env python3
"""
检查hsai_tasks表结构的脚本
"""

import sqlite3
import os

def check_table_structure():
    """检查hsai_tasks表结构"""
    
    # 数据库路径
    db_paths = [
        "data/webui.db",
        "./data/webui.db",
        "../data/webui.db",
        "c:/work/open-webui/backend/data/webui.db",
        "D:/Work/hsch/open-webui/backend/data/webui.db"
    ]
    
    db_conn = None
    for path in db_paths:
        try:
            if os.path.exists(path):
                db_conn = sqlite3.connect(path)
                print(f"✅ 连接到数据库: {path}")
                break
            else:
                print(f"❌ 数据库文件不存在: {path}")
        except Exception as e:
            print(f"❌ 无法连接到数据库 {path}: {e}")
            continue
    
    if not db_conn:
        print("❌ 无法连接到任何数据库")
        return
    
    try:
        cursor = db_conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_tasks'
        """)
        
        if not cursor.fetchone():
            print("❌ hsai_tasks 表不存在")
            return
        
        print("✅ hsai_tasks 表存在")
        
        # 查看表结构
        cursor.execute("PRAGMA table_info(hsai_tasks)")
        columns = cursor.fetchall()
        
        print("\n📋 hsai_tasks 表结构:")
        print("序号 | 字段名 | 数据类型 | 是否可为空 | 默认值 | 是否为主键")
        print("-" * 60)
        for i, col in enumerate(columns):
            print(f"{i+1:2d} | {col[1]:20s} | {col[2]:10s} | {col[3]:8s} | {col[4] or 'None':10s} | {col[5]}")
        
        # 检查是否有collaborators字段
        has_collaborators = any(col[1] == 'collaborators' for col in columns)
        print(f"\n🔍 collaborators 字段是否存在: {'✅ 是' if has_collaborators else '❌ 否'}")
        
        db_conn.close()
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {str(e)}")
        if db_conn:
            db_conn.close()

if __name__ == "__main__":
    check_table_structure()