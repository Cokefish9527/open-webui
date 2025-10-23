#!/usr/bin/env python3
"""
修复Redis队列消息表中的数据类型问题
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def fix_data_types():
    """修复数据类型问题"""
    try:
        # 导入数据库配置
        from open_webui.env import DATABASE_URL
        
        print(f"数据库URL: {DATABASE_URL}")
        
        # 检查数据库类型
        if "postgresql" in DATABASE_URL.lower():
            print("检测到PostgreSQL数据库")
            return fix_postgresql_data_types(DATABASE_URL)
        elif "sqlite" in DATABASE_URL.lower():
            print("检测到SQLite数据库，无需修复数据类型")
            return True
        else:
            print(f"不支持的数据库类型: {DATABASE_URL}")
            return False
            
    except Exception as e:
        print(f"修复过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_postgresql_data_types(database_url):
    """修复PostgreSQL数据库中的数据类型"""
    try:
        # 导入SQLAlchemy
        from sqlalchemy import create_engine, text
        
        # 创建数据库引擎
        engine = create_engine(database_url)
        
        # 检查当前列的数据类型
        check_types_sql = """
        SELECT column_name, data_type
        FROM information_schema.columns 
        WHERE table_name = 'redis_queue_messages' 
        AND column_name IN ('fetched_at', 'last_executed_at', 'retry_count', 'created_at', 'updated_at')
        ORDER BY column_name
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(check_types_sql))
            columns = result.fetchall()
            
            print("\n当前数据类型:")
            for col in columns:
                print(f"  {col[0]}: {col[1]}")
                
            # 检查是否需要修复
            needs_fix = False
            for col in columns:
                if col[0] in ['fetched_at', 'created_at', 'updated_at'] and col[1] != 'timestamp with time zone':
                    needs_fix = True
                    break
                if col[0] in ['last_executed_at', 'retry_count'] and col[1] != 'bigint':
                    needs_fix = True
                    break
                    
            if not needs_fix:
                print("数据类型已正确，无需修复")
                return True
                
            print("正在修复数据类型...")
            
            # 由于PostgreSQL不能直接修改列类型，我们需要：
            # 1. 添加临时列
            # 2. 复制数据
            # 3. 删除原列
            # 4. 重命名临时列
            
            # 这里我们只修复last_executed_at和retry_count列的类型
            fix_columns = [
                ('last_executed_at', 'bigint'),
                ('retry_count', 'bigint')
            ]
            
            for col_name, expected_type in fix_columns:
                # 检查当前类型
                current_type = next((col[1] for col in columns if col[0] == col_name), None)
                if current_type and current_type != expected_type:
                    print(f"修复 {col_name} 列类型: {current_type} -> {expected_type}")
                    # 添加临时列
                    temp_col_name = f"{col_name}_temp"
                    add_temp_sql = f"ALTER TABLE redis_queue_messages ADD COLUMN {temp_col_name} {expected_type}"
                    conn.execute(text(add_temp_sql))
                    
                    # 复制数据
                    copy_data_sql = f"UPDATE redis_queue_messages SET {temp_col_name} = {col_name}::bigint"
                    conn.execute(text(copy_data_sql))
                    
                    # 删除原列
                    drop_old_sql = f"ALTER TABLE redis_queue_messages DROP COLUMN {col_name}"
                    conn.execute(text(drop_old_sql))
                    
                    # 重命名临时列
                    rename_sql = f"ALTER TABLE redis_queue_messages RENAME COLUMN {temp_col_name} TO {col_name}"
                    conn.execute(text(rename_sql))
                    
            conn.commit()
            print("数据类型修复完成")
            return True
                
    except Exception as e:
        print(f"PostgreSQL数据类型修复过程中发生错误: {e}")
        return False

def main():
    print("Redis队列消息表数据类型修复工具")
    print("=" * 40)
    
    success = fix_data_types()
    if success:
        print("\n🎉 数据类型修复成功。")
        return 0
    else:
        print("\n❌ 数据类型修复失败。")
        return 1

if __name__ == "__main__":
    sys.exit(main())