import sqlite3
import os
from pathlib import Path

# 获取数据库路径
project_root = Path(__file__).parent.parent
data_dir = project_root / 'data'
db_path = data_dir / 'webui.db'

print(f"数据库路径: {db_path}")

if not db_path.exists():
    print("❌ 数据库文件不存在")
    exit(1)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 检查hsai_materials表的结构
    cursor.execute("PRAGMA table_info(hsai_materials)")
    columns = cursor.fetchall()
    
    print(f"\nhsai_materials表结构 (共{len(columns)}个字段):")
    has_is_deleted = False
    has_original_directory = False
    has_deleted_at = False
    has_deleted_by = False
    
    for col in columns:
        col_id, name, col_type, not_null, default_val, pk = col
        print(f"  {name}: {col_type} (not_null={not_null}, default={default_val})")
        
        if name == 'is_deleted':
            has_is_deleted = True
        elif name == 'original_directory':
            has_original_directory = True
        elif name == 'deleted_at':
            has_deleted_at = True
        elif name == 'deleted_by':
            has_deleted_by = True
    
    print(f"\n回收站字段检查:")
    print(f"  is_deleted: {'✅' if has_is_deleted else '❌'}")
    print(f"  original_directory: {'✅' if has_original_directory else '❌'}")
    print(f"  deleted_at: {'✅' if has_deleted_at else '❌'}")
    print(f"  deleted_by: {'✅' if has_deleted_by else '❌'}")
    
    # 检查现有数据
    cursor.execute("SELECT COUNT(*) FROM hsai_materials")
    total_materials = cursor.fetchone()[0]
    print(f"\n数据检查:")
    print(f"  总素材数: {total_materials}")
    
    if has_is_deleted:
        cursor.execute("SELECT COUNT(*) FROM hsai_materials WHERE is_deleted = 1")
        deleted_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM hsai_materials WHERE is_deleted = 0 OR is_deleted IS NULL")
        active_count = cursor.fetchone()[0]
        print(f"  已删除素材数: {deleted_count}")
        print(f"  活跃素材数: {active_count}")
        
        # 显示最近的素材信息
        cursor.execute("""
            SELECT id, name, is_deleted, original_directory, deleted_at 
            FROM hsai_materials 
            ORDER BY updated_at DESC 
            LIMIT 5
        """)
        recent_materials = cursor.fetchall()
        
        print(f"\n最近的5个素材:")
        for material in recent_materials:
            mat_id, name, is_deleted, orig_dir, deleted_at = material
            print(f"  {name}: is_deleted={is_deleted}, orig_dir={orig_dir}, deleted_at={deleted_at}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ 数据库检查异常: {e}")