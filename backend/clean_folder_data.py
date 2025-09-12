#!/usr/bin/env python3
"""
清理所有文件夹数据的脚本
注意：此操作不可逆，会删除所有HSAI素材文件夹数据
"""

import sqlite3
import time
import os
from typing import List, Dict

def backup_database(db_path: str) -> str:
    """创建数据库备份"""
    timestamp = int(time.time())
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        # 复制数据库文件
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 备份失败: {str(e)}")
        raise

def get_folder_statistics(db_path: str) -> Dict[str, int]:
    """获取清理前的文件夹统计信息"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_material_folders'
        """)
        
        if not cursor.fetchone():
            print("⚠️  hsai_material_folders 表不存在")
            conn.close()
            return {}
        
        stats = {}
        
        # 总文件夹数量
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders")
        stats['total'] = cursor.fetchone()[0]
        
        # 根文件夹数量
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id IS NULL")
        stats['root_folders'] = cursor.fetchone()[0]
        
        # 子文件夹数量
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id IS NOT NULL AND parent_id != ''")
        stats['child_folders'] = cursor.fetchone()[0]
        
        # 异常文件夹（parent_id为空字符串）
        cursor.execute("SELECT COUNT(*) FROM hsai_material_folders WHERE parent_id = ''")
        stats['invalid_folders'] = cursor.fetchone()[0]
        
        # 按用户统计
        cursor.execute("""
            SELECT user_id, COUNT(*) as count 
            FROM hsai_material_folders 
            GROUP BY user_id 
            ORDER BY count DESC
        """)
        user_stats = cursor.fetchall()
        stats['by_user'] = user_stats
        
        conn.close()
        return stats
        
    except Exception as e:
        print(f"❌ 获取统计信息失败: {str(e)}")
        return {}

def clean_folder_data(db_path: str, confirm: bool = False) -> bool:
    """清理所有文件夹数据"""
    if not confirm:
        print("❌ 需要确认参数才能执行清理操作")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️  开始清理文件夹数据...")
        
        # 删除所有文件夹记录
        cursor.execute("DELETE FROM hsai_material_folders")
        deleted_count = cursor.rowcount
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"✅ 清理完成，共删除 {deleted_count} 个文件夹记录")
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {str(e)}")
        return False

def clean_related_data(db_path: str, confirm: bool = False) -> bool:
    """清理相关的素材数据（可选）"""
    if not confirm:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️  开始清理相关素材数据...")
        
        # 检查素材表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_materials'
        """)
        
        if cursor.fetchone():
            # 清理素材记录（将folder_id设为NULL而不是删除记录）
            cursor.execute("UPDATE hsai_materials SET folder_id = NULL WHERE folder_id IS NOT NULL")
            updated_count = cursor.rowcount
            print(f"✅ 已将 {updated_count} 个素材的folder_id设为NULL")
        
        # 提交更改
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 清理相关数据失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("=== HSAI 文件夹数据清理工具 ===")
    print("⚠️  警告: 此操作将删除所有文件夹数据，无法恢复！")
    print()
    
    # 数据库文件路径
    db_paths = [
        "c:/work/open-webui/backend/data/webui.db",
        "./data/webui.db",
        "../data/webui.db",
        "data/webui.db"
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            print(f"✅ 找到数据库: {path}")
            break
    
    if not db_path:
        print("❌ 无法找到数据库文件")
        return
    
    # 获取清理前统计信息
    print("\n📊 清理前数据统计:")
    stats = get_folder_statistics(db_path)
    
    if not stats:
        print("❌ 无法获取数据统计信息")
        return
    
    print(f"   总文件夹数量: {stats.get('total', 0)}")
    print(f"   根文件夹数量: {stats.get('root_folders', 0)}")
    print(f"   子文件夹数量: {stats.get('child_folders', 0)}")
    print(f"   异常文件夹数量: {stats.get('invalid_folders', 0)}")
    
    print(f"\n👥 按用户分布:")
    for user_id, count in stats.get('by_user', [])[:5]:
        print(f"   用户 {user_id}: {count} 个文件夹")
    
    if stats.get('total', 0) == 0:
        print("✅ 数据库中没有文件夹数据，无需清理")
        return
    
    # 确认操作
    print(f"\n⚠️  即将删除 {stats.get('total', 0)} 个文件夹记录")
    print("此操作不可逆！")
    
    confirm = input("\n是否继续？请输入 'YES' 确认: ")
    if confirm != 'YES':
        print("❌ 操作已取消")
        return
    
    # 创建备份
    print("\n💾 创建数据库备份...")
    try:
        backup_path = backup_database(db_path)
    except Exception as e:
        print(f"❌ 备份失败，操作终止: {str(e)}")
        return
    
    # 执行清理
    print(f"\n🗑️  开始清理操作...")
    
    # 清理文件夹数据
    success = clean_folder_data(db_path, confirm=True)
    if not success:
        print("❌ 文件夹数据清理失败")
        return
    
    # 询问是否清理相关素材数据
    clean_materials = input("\n是否同时清理素材的folder_id关联？(y/N): ")
    if clean_materials.lower() in ['y', 'yes']:
        clean_related_data(db_path, confirm=True)
    
    # 验证清理结果
    print(f"\n📊 清理后数据统计:")
    final_stats = get_folder_statistics(db_path)
    print(f"   剩余文件夹数量: {final_stats.get('total', 0)}")
    
    print(f"\n✅ 清理完成！")
    print(f"📁 数据库备份位置: {backup_path}")
    print(f"如需恢复数据，请将备份文件重命名为 webui.db")

if __name__ == "__main__":
    main()