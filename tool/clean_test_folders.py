#!/usr/bin/env python3
"""
快速清理测试文件夹数据的脚本
仅清理测试和调试相关的文件夹，保留正常的业务数据
"""

import sqlite3
import time

def clean_test_folders():
    """清理测试相关的文件夹"""
    print("=== 清理测试文件夹数据 ===")
    
    db_path = "c:/work/open-webui/backend/data/webui.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取清理前统计
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE name LIKE 'test_%' OR name LIKE 'debug_%'")
        test_count = cursor.fetchone()[0]
        
        print(f"📊 找到 {test_count} 个测试文件夹")
        
        if test_count == 0:
            print("✅ 没有测试文件夹需要清理")
            conn.close()
            return
        
        # 清理测试文件夹
        cursor.execute("DELETE FROM hsai_material_folders WHERE name LIKE 'test_%' OR name LIKE 'debug_%'")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ 已清理 {deleted_count} 个测试文件夹")
        
    except Exception as e:
        print(f"❌ 清理失败: {str(e)}")

def clean_empty_string_parent_ids():
    """修复空字符串的parent_id"""
    print("\n=== 修复异常的parent_id ===")
    
    db_path = "c:/work/open-webui/backend/data/webui.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查异常的parent_id
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id = ''")
        invalid_count = cursor.fetchone()[0]
        
        print(f"📊 找到 {invalid_count} 个异常的parent_id")
        
        if invalid_count > 0:
            # 修复空字符串为NULL
            cursor.execute("UPDATE hsai_material_folders SET parent_id = NULL WHERE parent_id = ''")
            fixed_count = cursor.rowcount
            
            conn.commit()
            print(f"✅ 已修复 {fixed_count} 个异常的parent_id")
        else:
            print("✅ 没有异常的parent_id需要修复")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 修复失败: {str(e)}")

if __name__ == "__main__":
    clean_test_folders()
    clean_empty_string_parent_ids()
    print("\n🎉 清理完成！")