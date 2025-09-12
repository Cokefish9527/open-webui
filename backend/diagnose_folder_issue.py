#!/usr/bin/env python3
"""
文件夹创建问题诊断脚本
用于检查数据库状态和调试文件夹创建问题
"""

import sys
import os
import sqlite3
import time
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "backend"))

def check_database_schema():
    """检查数据库表结构"""
    print("=== 检查数据库表结构 ===")
    
    # 尝试查找数据库文件
    possible_db_paths = [
        "backend/open_webui/data/webui.db",
        "backend/data/webui.db", 
        "data/webui.db",
        "webui.db"
    ]
    
    db_path = None
    for path in possible_db_paths:
        full_path = project_root / path
        if full_path.exists():
            db_path = full_path
            break
    
    if not db_path:
        print("❌ 未找到数据库文件")
        print("   可能的路径:")
        for path in possible_db_paths:
            print(f"   - {project_root / path}")
        return False
    
    print(f"✅ 找到数据库文件: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查 hsai_material_folders 表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hsai_material_folders'
        """)
        result = cursor.fetchone()
        
        if result:
            print("✅ hsai_material_folders 表存在")
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(hsai_material_folders)")
            columns = cursor.fetchall()
            print("表结构:")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})" + (", NOT NULL" if col[3] else ""))
            
            # 检查外键约束
            cursor.execute("PRAGMA foreign_key_list(hsai_material_folders)")
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                print("外键约束:")
                for fk in foreign_keys:
                    print(f"   - {fk[3]} -> {fk[2]}.{fk[4]}")
            else:
                print("⚠️  未找到外键约束定义")
            
            # 检查现有数据
            cursor.execute("SELECT COUNT(*) FROM hsai_material_folders")
            count = cursor.fetchone()[0]
            print(f"现有记录数: {count}")
            
            if count > 0:
                cursor.execute("""
                    SELECT id, name, parent_id, user_id 
                    FROM hsai_material_folders 
                    LIMIT 5
                """)
                samples = cursor.fetchall()
                print("示例数据:")
                for sample in samples:
                    print(f"   - ID: {sample[0]}, Name: {sample[1]}, Parent: {sample[2]}, User: {sample[3]}")
        else:
            print("❌ hsai_material_folders 表不存在")
            return False
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {str(e)}")
        return False

def test_folder_creation_directly():
    """直接测试文件夹创建逻辑"""
    print("\n=== 直接测试文件夹创建逻辑 ===")
    
    try:
        # 导入必要的模块
        from open_webui.models.hsai_materials import HSAIMaterialFolders, HSAIMaterialFolderForm
        
        # 创建测试用户ID
        test_user_id = "test_user_123"
        
        # 测试1: 创建根文件夹
        print("测试1: 创建根文件夹")
        root_form = HSAIMaterialFolderForm(
            name=f"test_root_{int(time.time())}",
            description="测试根文件夹"
        )
        
        root_folder = HSAIMaterialFolders.insert_new_folder(test_user_id, root_form)
        if root_folder:
            print(f"✅ 根文件夹创建成功: {root_folder.name} (ID: {root_folder.id})")
            
            # 测试2: 创建子文件夹
            print("测试2: 创建子文件夹")
            sub_form = HSAIMaterialFolderForm(
                name=f"test_sub_{int(time.time())}",
                description="测试子文件夹",
                parent_id=root_folder.id
            )
            
            sub_folder = HSAIMaterialFolders.insert_new_folder(test_user_id, sub_form)
            if sub_folder:
                print(f"✅ 子文件夹创建成功: {sub_folder.name} (ID: {sub_folder.id})")
                print(f"   父文件夹ID: {sub_folder.parent_id}")
            else:
                print("❌ 子文件夹创建失败")
                return False
            
            # 测试3: 使用无效的parent_id
            print("测试3: 使用无效的parent_id")
            invalid_form = HSAIMaterialFolderForm(
                name=f"test_invalid_{int(time.time())}",
                description="测试无效父目录",
                parent_id="invalid_parent_id_12345"
            )
            
            invalid_folder = HSAIMaterialFolders.insert_new_folder(test_user_id, invalid_form)
            if invalid_folder:
                print("❌ 无效parent_id应该被拒绝，但创建成功了")
                return False
            else:
                print("✅ 无效parent_id正确被拒绝")
            
            # 测试4: 重复名称
            print("测试4: 重复文件夹名称")
            duplicate_form = HSAIMaterialFolderForm(
                name=sub_folder.name,
                description="重复名称测试",
                parent_id=root_folder.id
            )
            
            duplicate_folder = HSAIMaterialFolders.insert_new_folder(test_user_id, duplicate_form)
            if duplicate_folder:
                print("❌ 重复名称应该被拒绝，但创建成功了")
                return False
            else:
                print("✅ 重复名称正确被拒绝")
            
            print("\n✅ 所有直接测试通过！")
            return True
        else:
            print("❌ 根文件夹创建失败")
            return False
            
    except ImportError as e:
        print(f"❌ 导入模块失败: {str(e)}")
        print("   请确保在正确的Python环境中运行此脚本")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=== 文件夹创建问题诊断 ===")
    print(f"项目根目录: {project_root}")
    
    # 检查数据库
    db_ok = check_database_schema()
    
    if db_ok:
        # 直接测试
        test_ok = test_folder_creation_directly()
        
        if test_ok:
            print("\n🎉 诊断完成！文件夹创建功能正常。")
            print("\n如果API仍有问题，请检查:")
            print("1. 服务器是否正在运行")
            print("2. 认证token是否有效")
            print("3. API路由配置是否正确")
        else:
            print("\n❌ 发现问题！请检查错误日志。")
    else:
        print("\n❌ 数据库检查失败，无法继续测试。")

if __name__ == "__main__":
    main()