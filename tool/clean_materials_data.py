#!/usr/bin/env python3
"""
清理所有素材数据的脚本
注意：此操作不可逆，会删除所有HSAI素材数据
"""

import sqlite3
import time
import os
import shutil
from typing import List, Dict, Tuple

def backup_database(db_path: str) -> str:
    """创建数据库备份"""
    timestamp = int(time.time())
    backup_path = f"{db_path}.materials_backup_{timestamp}"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 备份失败: {str(e)}")
        raise

def get_materials_statistics(db_path: str) -> Dict[str, any]:
    """获取清理前的素材统计信息"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_materials'
        """)
        
        if not cursor.fetchone():
            print("⚠️  hsai_materials 表不存在")
            conn.close()
            return {}
        
        stats = {}
        
        # 总素材数量
        cursor.execute("SELECT COUNT(*) FROM hsai_materials")
        stats['total'] = cursor.fetchone()[0]
        
        # 按状态统计
        cursor.execute("SELECT status, COUNT(*) FROM hsai_materials GROUP BY status")
        status_stats = cursor.fetchall()
        stats['by_status'] = dict(status_stats)
        
        # 按素材类型统计
        cursor.execute("SELECT material_type, COUNT(*) FROM hsai_materials GROUP BY material_type")
        type_stats = cursor.fetchall()
        stats['by_type'] = dict(type_stats)
        
        # 按用户统计（前10个）
        cursor.execute("""
            SELECT user_id, COUNT(*) as count 
            FROM hsai_materials 
            GROUP BY user_id 
            ORDER BY count DESC 
            LIMIT 10
        """)
        user_stats = cursor.fetchall()
        stats['by_user'] = user_stats
        
        # 已删除的素材统计
        cursor.execute("SELECT COUNT(*) FROM hsai_materials WHERE is_deleted = 1")
        stats['deleted_count'] = cursor.fetchone()[0]
        
        # 有文件路径的素材统计
        cursor.execute("SELECT COUNT(*) FROM hsai_materials WHERE file_path IS NOT NULL AND file_path != ''")
        stats['with_files'] = cursor.fetchone()[0]
        
        # 文件大小统计
        cursor.execute("SELECT SUM(file_size) FROM hsai_materials WHERE file_size IS NOT NULL")
        total_size_result = cursor.fetchone()[0]
        stats['total_file_size'] = total_size_result if total_size_result else 0
        
        # 有folder_id关联的素材
        cursor.execute("SELECT COUNT(*) FROM hsai_materials WHERE folder_id IS NOT NULL AND folder_id != ''")
        stats['with_folder'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
        
    except Exception as e:
        print(f"❌ 获取统计信息失败: {str(e)}")
        return {}

def get_file_operation_logs_stats(db_path: str) -> Dict[str, any]:
    """获取文件操作日志统计"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_file_operation_logs'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return {'exists': False}
        
        stats = {'exists': True}
        
        # 总日志数量
        cursor.execute("SELECT COUNT(*) FROM hsai_file_operation_logs")
        stats['total'] = cursor.fetchone()[0]
        
        # 按操作类型统计
        cursor.execute("SELECT operation_type, COUNT(*) FROM hsai_file_operation_logs GROUP BY operation_type")
        operation_stats = cursor.fetchall()
        stats['by_operation'] = dict(operation_stats)
        
        conn.close()
        return stats
        
    except Exception as e:
        print(f"❌ 获取操作日志统计失败: {str(e)}")
        return {'exists': False}

def clean_materials_data(db_path: str, confirm: bool = False) -> bool:
    """清理所有素材数据"""
    if not confirm:
        print("❌ 需要确认参数才能执行清理操作")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️  开始清理素材数据...")
        
        # 删除所有素材记录
        cursor.execute("DELETE FROM hsai_materials")
        deleted_count = cursor.rowcount
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"✅ 清理完成，共删除 {deleted_count} 个素材记录")
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {str(e)}")
        return False

def clean_file_operation_logs(db_path: str, confirm: bool = False) -> bool:
    """清理文件操作日志"""
    if not confirm:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_file_operation_logs'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return True
        
        print("🗑️  开始清理文件操作日志...")
        
        # 删除所有操作日志
        cursor.execute("DELETE FROM hsai_file_operation_logs")
        deleted_count = cursor.rowcount
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"✅ 已清理 {deleted_count} 个文件操作日志记录")
        return True
        
    except Exception as e:
        print(f"❌ 清理文件操作日志失败: {str(e)}")
        return False

def clean_material_tags(db_path: str, confirm: bool = False) -> bool:
    """清理素材标签数据"""
    if not confirm:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_material_tags'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return True
        
        print("🗑️  开始清理素材标签...")
        
        # 删除所有标签
        cursor.execute("DELETE FROM hsai_material_tags")
        deleted_count = cursor.rowcount
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"✅ 已清理 {deleted_count} 个标签记录")
        return True
        
    except Exception as e:
        print(f"❌ 清理标签失败: {str(e)}")
        return False

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def main():
    """主函数"""
    print("=== HSAI 素材数据清理工具 ===")
    print("⚠️  警告: 此操作将删除所有素材数据，无法恢复！")
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
    
    # 素材统计
    materials_stats = get_materials_statistics(db_path)
    if not materials_stats:
        print("❌ 无法获取素材统计信息")
        return
    
    print(f"   总素材数量: {materials_stats.get('total', 0)}")
    
    if materials_stats.get('total', 0) == 0:
        print("✅ 数据库中没有素材数据，无需清理")
        return
    
    print(f"   已删除素材: {materials_stats.get('deleted_count', 0)}")
    print(f"   有文件路径的素材: {materials_stats.get('with_files', 0)}")
    print(f"   关联文件夹的素材: {materials_stats.get('with_folder', 0)}")
    print(f"   总文件大小: {format_file_size(materials_stats.get('total_file_size', 0))}")
    
    # 按状态统计
    print(f"\n📈 按状态统计:")
    for status, count in materials_stats.get('by_status', {}).items():
        print(f"   {status}: {count}")
    
    # 按类型统计
    print(f"\n📂 按类型统计:")
    for material_type, count in materials_stats.get('by_type', {}).items():
        print(f"   {material_type}: {count}")
    
    # 按用户统计
    print(f"\n👥 按用户分布 (前10个):")
    for user_id, count in materials_stats.get('by_user', []):
        print(f"   用户 {user_id}: {count} 个素材")
    
    # 文件操作日志统计
    logs_stats = get_file_operation_logs_stats(db_path)
    if logs_stats.get('exists'):
        print(f"\n📋 文件操作日志:")
        print(f"   总日志数量: {logs_stats.get('total', 0)}")
        for operation, count in logs_stats.get('by_operation', {}).items():
            print(f"   {operation}: {count}")
    
    # 确认操作
    print(f"\n⚠️  即将删除:")
    print(f"   - {materials_stats.get('total', 0)} 个素材记录")
    if logs_stats.get('exists'):
        print(f"   - {logs_stats.get('total', 0)} 个操作日志记录")
    print("   - 所有相关的标签数据")
    print("\n此操作不可逆！")
    
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
    
    success = True
    
    # 1. 清理素材数据
    if not clean_materials_data(db_path, confirm=True):
        success = False
    
    # 2. 清理文件操作日志
    if logs_stats.get('exists'):
        clean_logs = input("\n是否同时清理文件操作日志？(y/N): ")
        if clean_logs.lower() in ['y', 'yes']:
            if not clean_file_operation_logs(db_path, confirm=True):
                success = False
    
    # 3. 清理标签数据
    clean_tags = input("\n是否同时清理素材标签？(y/N): ")
    if clean_tags.lower() in ['y', 'yes']:
        if not clean_material_tags(db_path, confirm=True):
            success = False
    
    # 验证清理结果
    print(f"\n📊 清理后数据统计:")
    final_stats = get_materials_statistics(db_path)
    print(f"   剩余素材数量: {final_stats.get('total', 0)}")
    
    if success:
        print(f"\n✅ 清理完成！")
    else:
        print(f"\n⚠️  清理过程中遇到部分问题，请检查日志")
    
    print(f"📁 数据库备份位置: {backup_path}")
    print(f"如需恢复数据，请将备份文件重命名为 webui.db")

if __name__ == "__main__":
    main()
