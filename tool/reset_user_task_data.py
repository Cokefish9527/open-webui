#!/usr/bin/env python3
"""
还原用户任务数据，将当前的蓝图数据、任务数据删除，账号还原到触发蓝图节点之前的状态
"""

import sqlite3
import argparse
import os
from datetime import datetime

def get_database_connection(db_path):
    """获取数据库连接"""
    try:
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            return None
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ 无法连接到数据库: {e}")
        return None

def reset_user_data(conn, user_id):
    """重置用户数据"""
    try:
        cursor = conn.cursor()
        
        print(f"🔄 开始重置用户 {user_id} 的数据...")
        
        # 1. 删除用户的所有任务
        cursor.execute("DELETE FROM hsai_tasks WHERE user_id = ?", (user_id,))
        tasks_deleted = cursor.rowcount
        print(f"   删除任务记录: {tasks_deleted} 条")
        
        # 2. 删除用户的蓝图进度记录
        cursor.execute("DELETE FROM hsai_blueprint_progress WHERE project_id IN (SELECT id FROM hsai_projects WHERE user_id = ?)", (user_id,))
        blueprint_deleted = cursor.rowcount
        print(f"   删除蓝图进度记录: {blueprint_deleted} 条")
        
        # 3. 删除用户的任务蓝图链接记录
        cursor.execute("DELETE FROM hsai_task_blueprint_links WHERE task_id IN (SELECT id FROM hsai_tasks WHERE user_id = ?)", (user_id,))
        links_deleted = cursor.rowcount
        print(f"   删除任务蓝图链接: {links_deleted} 条")
        
        # 4. 删除用户的项目
        cursor.execute("DELETE FROM hsai_projects WHERE user_id = ?", (user_id,))
        projects_deleted = cursor.rowcount
        print(f"   删除项目记录: {projects_deleted} 个")
        
        # 5. 删除用户的公司
        cursor.execute("DELETE FROM companies WHERE owner_user_id = ?", (user_id,))
        companies_deleted = cursor.rowcount
        print(f"   删除公司记录: {companies_deleted} 个")
        
        # 6. 删除任务状态日志
        cursor.execute("DELETE FROM hsai_task_state_logs WHERE task_id IN (SELECT id FROM hsai_tasks WHERE user_id = ?)", (user_id,))
        logs_deleted = cursor.rowcount
        print(f"   删除任务状态日志: {logs_deleted} 条")
        
        # 7. 重置用户的业务信息收集状态
        cursor.execute("UPDATE user SET info_collection_completed = 0 WHERE id = ?", (user_id,))
        users_updated = cursor.rowcount
        print(f"   重置用户信息收集状态: {users_updated} 个")
        
        # 提交事务
        conn.commit()
        
        print(f"\n✅ 用户 {user_id} 的数据重置完成")
        print(f"   总计删除记录: {tasks_deleted + blueprint_deleted + links_deleted + projects_deleted + companies_deleted + logs_deleted} 条")
        
        return True
        
    except Exception as e:
        print(f"❌ 重置用户数据时发生错误: {e}")
        conn.rollback()
        return False

def verify_user_exists(conn, user_id):
    """验证用户是否存在"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email FROM user WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            print(f"✅ 找到用户: {user['name']} ({user['email']})")
            return True
        else:
            print(f"❌ 未找到用户ID为 {user_id} 的用户")
            return False
    except Exception as e:
        print(f"❌ 验证用户时发生错误: {e}")
        return False

def show_user_data_summary(conn, user_id):
    """显示用户当前数据摘要"""
    try:
        cursor = conn.cursor()
        
        # 查询任务数量
        cursor.execute("SELECT COUNT(*) as count FROM hsai_tasks WHERE user_id = ?", (user_id,))
        tasks_count = cursor.fetchone()['count']
        
        # 查询项目数量
        cursor.execute("SELECT COUNT(*) as count FROM hsai_projects WHERE user_id = ?", (user_id,))
        projects_count = cursor.fetchone()['count']
        
        # 查询公司数量
        cursor.execute("SELECT COUNT(*) as count FROM companies WHERE owner_user_id = ?", (user_id,))
        companies_count = cursor.fetchone()['count']
        
        print(f"\n📊 用户 {user_id} 当前数据摘要:")
        print(f"   任务数量: {tasks_count}")
        print(f"   项目数量: {projects_count}")
        print(f"   公司数量: {companies_count}")
        
    except Exception as e:
        print(f"❌ 获取数据摘要时发生错误: {e}")

def main():
    parser = argparse.ArgumentParser(description="还原用户任务数据")
    parser.add_argument("--user-id", required=True, help="用户ID")
    parser.add_argument("--db-path", default="data/webui.db", help="数据库文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅显示将要执行的操作，不实际执行")
    
    args = parser.parse_args()
    
    print("🔄 开始还原用户任务数据...")
    print(f"   用户ID: {args.user_id}")
    print(f"   数据库路径: {args.db_path}")
    print(f"   模拟运行: {'是' if args.dry_run else '否'}")
    
    # 获取数据库连接
    conn = get_database_connection(args.db_path)
    if not conn:
        return 1
    
    try:
        # 验证用户是否存在
        if not verify_user_exists(conn, args.user_id):
            conn.close()
            return 1
        
        # 显示当前数据摘要
        show_user_data_summary(conn, args.user_id)
        
        if args.dry_run:
            print("\n🔍 模拟运行模式 - 仅显示将要执行的操作")
            print("   将执行以下删除操作:")
            print("   1. 删除用户的所有任务记录")
            print("   2. 删除用户的蓝图进度记录")
            print("   3. 删除用户的任务蓝图链接记录")
            print("   4. 删除用户的项目记录")
            print("   5. 删除用户的公司记录")
            print("   6. 删除用户的任务状态日志")
            print("   7. 重置用户的信息收集状态")
            print("\n💡 如需实际执行，请移除 --dry-run 参数")
        else:
            # 确认执行
            confirm = input("\n⚠️  确定要删除用户的所有相关数据吗？此操作不可恢复！(输入 'yes' 确认): ")
            if confirm.lower() != 'yes':
                print("❌ 操作已取消")
                conn.close()
                return 0
            
            # 执行数据重置
            if reset_user_data(conn, args.user_id):
                print("\n✅ 数据重置成功完成")
                print("💡 用户数据已还原到触发蓝图节点之前的状态")
            else:
                print("\n❌ 数据重置失败")
                conn.close()
                return 1
        
        # 再次显示数据摘要
        if not args.dry_run:
            show_user_data_summary(conn, args.user_id)
        
        conn.close()
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ 操作被用户中断")
        conn.close()
        return 1
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        conn.close()
        return 1

if __name__ == "__main__":
    exit(main())