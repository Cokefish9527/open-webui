import sqlite3
import psycopg2
import json
from psycopg2 import sql
from datetime import datetime
import time

# SQLite数据库路径
SQLITE_DB_PATH = 'd:/Work/hsch/open-webui/backend/data/webui.db'

# PostgreSQL数据库连接配置
PG_HOST = "pgm-bp1x8d937cl58d1afo.pg.rds.aliyuncs.com"
PG_PORT = "5432"
PG_USER = "hsai"
PG_PASSWORD = "c5agLR)ah28vnA3+%Yyn"
PG_DB_NAME = "Owen_ai"

def connect_sqlite():
    """连接到SQLite数据库"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    # 设置返回字典格式
    conn.row_factory = sqlite3.Row
    return conn

def connect_postgresql():
    """连接到PostgreSQL数据库"""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DB_NAME
    )

def get_table_names_sqlite(conn):
    """获取SQLite数据库中的所有表名"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def get_column_names_sqlite(conn, table_name):
    """获取SQLite表的列名"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.close()
    return columns

def export_table_data_sqlite(conn, table_name):
    """从SQLite导出表数据"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    cursor.close()
    return rows

def convert_timestamp(value):
    """转换时间戳值"""
    if value is None:
        return None
    
    try:
        # 如果是字符串形式的时间戳
        if isinstance(value, str):
            if value.isdigit():
                timestamp = int(value)
            else:
                # 如果已经是日期格式，直接返回
                return value
        elif isinstance(value, (int, float)):
            timestamp = int(value)
        else:
            return value
        
        # 处理毫秒和秒的时间戳
        if timestamp > 9999999999:  # 可能是毫秒
            timestamp = timestamp / 1000
        
        # 转换为PostgreSQL可接受的格式
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, OSError, TypeError):
        # 如果转换失败，返回原始值
        return value

def convert_boolean(value):
    """转换布尔值"""
    if value is None:
        return None
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'active')
    return bool(value)

def convert_json(value):
    """转换JSON值"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            # 验证是否为有效的JSON
            json.loads(value)
            return value
        except json.JSONDecodeError:
            # 如果不是有效的JSON，转换为JSON字符串
            return json.dumps(str(value))
    else:
        return json.dumps(value)

def convert_value_for_postgresql(value, column_name, table_name):
    """根据列名和表名转换值以适配PostgreSQL"""
    if value is None:
        return None
    
    # 特殊处理时间戳字段
    timestamp_columns = [
        'created_at', 'updated_at', 'last_active_at', 'started_at', 
        'completed_at', 'published_at', 'consumed_at', 'timestamp',
        'last_executed_at', 'token_expires_at', 'scheduled_at',
        'processed_at', 'learned_at', 'last_stats_update_at', 'migrated_at'
    ]
    
    if column_name in timestamp_columns:
        return convert_timestamp(value)
    
    # 特殊处理布尔类型字段
    boolean_columns = [
        'is_deleted', 'is_pinned', 'is_collapsed', 'is_super_admin', 
        'is_org_admin', 'active', 'archived', 'is_expanded', 'info_collection_completed'
    ]
    
    if column_name in boolean_columns:
        return convert_boolean(value)
    
    # 特殊处理JSON类型字段
    json_columns = [
        'settings', 'info', 'meta', 'data', 'config', 'access_control', 
        'definition', 'variables', 'tags', 'material_metadata', 'ai_analysis', 
        'items', 'permissions', 'content', 'detail', 'inputs', 'outputs', 
        'execution_log', 'publish_data', 'response_data', 'metrics', 
        'previous_metrics', 'growth_rate', 'company_info', 'config_value',
        'collaborators', 'shared_sessions', 'position', 'style', 'actions'
    ]
    
    if column_name in json_columns:
        return convert_json(value)
    
    # 特殊处理active字段，确保是整数
    if column_name == 'active' and table_name == 'auth':
        if isinstance(value, bool):
            return 1 if value else 0
        elif isinstance(value, str):
            return 1 if value.lower() in ('true', '1', 'yes', 'on') else 0
        else:
            return int(bool(value))
    
    return value

def get_postgresql_table_name(table_name):
    """获取PostgreSQL中的表名（处理关键字）"""
    # 处理SQL关键字
    if table_name == 'group':
        return '"group"'
    elif table_name == 'user':
        return '"user"'
    else:
        return table_name

def disable_foreign_key_constraints(conn):
    """禁用外键约束"""
    cursor = conn.cursor()
    try:
        cursor.execute("SET session_replication_role = 'replica';")
        conn.commit()
        print("已禁用外键约束")
    except Exception as e:
        print(f"禁用外键约束时出错: {e}")
    finally:
        cursor.close()

def enable_foreign_key_constraints(conn):
    """启用外键约束"""
    cursor = conn.cursor()
    try:
        cursor.execute("SET session_replication_role = 'origin';")
        conn.commit()
        print("已启用外键约束")
    except Exception as e:
        print(f"启用外键约束时出错: {e}")
    finally:
        cursor.close()

def import_table_data_postgresql(conn, table_name, columns, rows):
    """将数据导入到PostgreSQL"""
    if not rows:
        print(f"表 {table_name} 没有数据需要导入")
        return
    
    pg_table_name = get_postgresql_table_name(table_name)
    cursor = conn.cursor()
    
    # 过滤掉PostgreSQL表中不存在的列
    if table_name == 'user':
        # 移除SQLite中存在但PostgreSQL中不存在的列
        filtered_columns = [col for col in columns if col not in ['credit_balance']]
        filtered_rows = []
        for row in rows:
            filtered_row = []
            for i, col in enumerate(columns):
                if col not in ['credit_balance']:
                    filtered_row.append(row[i])
            filtered_rows.append(tuple(filtered_row))
        columns = filtered_columns
        rows = filtered_rows
    
    # 构建INSERT语句
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join([f'"{col}"' for col in columns])
    insert_query = f'INSERT INTO {pg_table_name} ({column_names}) VALUES ({placeholders})'
    
    # 转换数据
    converted_rows = []
    for row in rows:
        converted_row = []
        for i, value in enumerate(row):
            column_name = columns[i]
            converted_value = convert_value_for_postgresql(value, column_name, table_name)
            converted_row.append(converted_value)
        converted_rows.append(tuple(converted_row))
    
    # 批量插入数据
    try:
        cursor.executemany(insert_query, converted_rows)
        conn.commit()
        print(f"  成功导入 {len(rows)} 行数据到表 {table_name}")
    except Exception as e:
        print(f"  导入表 {table_name} 数据时出错: {e}")
        conn.rollback()
    finally:
        cursor.close()

def migrate_table(conn_sqlite, conn_postgresql, table_name):
    """迁移单个表的数据"""
    print(f"正在迁移表: {table_name}")
    
    # 跳过某些系统表或不需要迁移的表
    if table_name in ['sqlite_sequence', 'alembic_version']:
        print(f"  跳过系统表 {table_name}")
        return
    
    # 跳过不存在于PostgreSQL中的表
    if table_name in ['redis_queue_messages']:
        print(f"  跳过表 {table_name} (PostgreSQL中不存在)")
        return
    
    # 获取表结构
    columns = get_column_names_sqlite(conn_sqlite, table_name)
    print(f"  列名: {columns}")
    
    # 导出数据
    rows = export_table_data_sqlite(conn_sqlite, table_name)
    print(f"  数据行数: {len(rows)}")
    
    # 导入数据
    import_table_data_postgresql(conn_postgresql, table_name, columns, rows)

def main():
    """主函数"""
    # 连接数据库
    conn_sqlite = connect_sqlite()
    conn_postgresql = connect_postgresql()
    
    try:
        # 禁用外键约束以避免导入时冲突
        disable_foreign_key_constraints(conn_postgresql)
        
        # 获取所有表名
        tables = get_table_names_sqlite(conn_sqlite)
        print(f"找到 {len(tables)} 个表: {tables}")
        
        # 定义迁移顺序，确保被引用的表先迁移
        migration_order = [
            'migratehistory',
            'companies',      # 先迁移公司表
            'auth',           # 认证表
            'user',           # 用户表（被其他表引用）
            'hsai_projects',  # 项目表
            'hsai_workflows', # 工作流表
            'hsai_material_folders',  # 素材文件夹表
            # 其他表按字母顺序
        ]
        
        # 添加未在迁移顺序中的表
        for table in tables:
            if table not in migration_order and table not in ['sqlite_sequence', 'alembic_version']:
                migration_order.append(table)
        
        # 按顺序迁移每个表的数据
        for table_name in migration_order:
            if table_name in tables:
                try:
                    migrate_table(conn_sqlite, conn_postgresql, table_name)
                except Exception as e:
                    print(f"迁移表 {table_name} 时出错: {e}")
            else:
                print(f"表 {table_name} 不存在于SQLite数据库中")
        
        # 重新启用外键约束
        enable_foreign_key_constraints(conn_postgresql)
        
        print("数据迁移完成")
        
    except Exception as e:
        print(f"数据迁移过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭连接
        conn_sqlite.close()
        conn_postgresql.close()

if __name__ == "__main__":
    main()