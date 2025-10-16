import sqlite3
import psycopg2
import json
from psycopg2 import sql
from datetime import datetime

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
    return sqlite3.connect(SQLITE_DB_PATH)

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

def convert_value_for_postgresql(value, column_name, table_name):
    """转换值以适配PostgreSQL"""
    if value is None:
        return None
    
    # 特殊处理布尔类型字段
    if column_name in ['is_deleted', 'is_pinned', 'is_collapsed', 'is_super_admin', 'is_org_admin', 'active', 'archived']:
        if isinstance(value, int):
            return bool(value)
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
    
    # 特殊处理时间戳字段
    if column_name in ['created_at', 'updated_at', 'last_active_at', 'started_at', 'completed_at', 'published_at', 'consumed_at']:
        if isinstance(value, (int, float)) and value > 0:
            # 将Unix时间戳转换为PostgreSQL时间戳格式
            try:
                # 检查是否为毫秒时间戳
                if value > 9999999999:  # 大于这个值可能是毫秒
                    dt = datetime.fromtimestamp(value / 1000)
                else:
                    dt = datetime.fromtimestamp(value)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, OSError):
                # 如果转换失败，保持原值
                return value
        elif isinstance(value, str) and value.isdigit():
            try:
                timestamp = int(value)
                if timestamp > 9999999999:  # 大于这个值可能是毫秒
                    dt = datetime.fromtimestamp(timestamp / 1000)
                else:
                    dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, OSError):
                return value
    
    # 处理JSON类型字段
    if column_name in ['settings', 'info', 'meta', 'data', 'config', 'access_control', 'definition', 'variables', 
                      'tags', 'material_metadata', 'ai_analysis', 'items', 'permissions', 'content', 'detail',
                      'inputs', 'outputs', 'execution_log', 'publish_data', 'response_data', 'metrics', 
                      'previous_metrics', 'growth_rate', 'company_info', 'config_value']:
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
    
    return value

def import_table_data_postgresql(conn, table_name, columns, rows):
    """将数据导入到PostgreSQL"""
    if not rows:
        print(f"表 {table_name} 没有数据需要导入")
        return
    
    # 处理特殊表名
    if table_name == 'group':
        pg_table_name = '"group"'
    else:
        pg_table_name = table_name
    
    cursor = conn.cursor()
    
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
        converted_rows.append(converted_row)
    
    # 批量插入数据
    try:
        cursor.executemany(insert_query, converted_rows)
        conn.commit()
        print(f"成功导入 {len(rows)} 行数据到表 {table_name}")
    except Exception as e:
        print(f"导入表 {table_name} 数据时出错: {e}")
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
        # 获取所有表名
        tables = get_table_names_sqlite(conn_sqlite)
        print(f"找到 {len(tables)} 个表: {tables}")
        
        # 定义迁移顺序，确保被引用的表先迁移
        migration_order = [
            'companies',  # 先迁移公司表
            'user',       # 用户表（被其他表引用）
            'auth',       # 认证表
            'hsai_projects',  # 项目表
            'hsai_material_folders',  # 素材文件夹表
            'hsai_workflows',  # 工作流表
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
        
        print("数据迁移完成")
        
    except Exception as e:
        print(f"数据迁移过程中出错: {e}")
    finally:
        # 关闭连接
        conn_sqlite.close()
        conn_postgresql.close()

if __name__ == "__main__":
    main()