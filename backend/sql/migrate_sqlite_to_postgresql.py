import sqlite3
import psycopg2
import json
from psycopg2 import sql

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

def get_table_schema_sqlite(conn, table_name):
    """获取SQLite表的结构信息"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    cursor.close()
    return columns

def export_table_data_sqlite(conn, table_name):
    """从SQLite导出表数据"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    cursor.close()
    return rows

def get_column_names_sqlite(conn, table_name):
    """获取SQLite表的列名"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.close()
    return columns

def convert_sqlite_value(value, column_type):
    """转换SQLite值以适配PostgreSQL"""
    if value is None:
        return None
    
    # 处理JSON类型
    if column_type in ['JSON', 'JSONB']:
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
    
    # 处理布尔类型
    if column_type == 'BOOLEAN':
        if isinstance(value, int):
            return bool(value)
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
    
    # 处理时间戳
    if column_type in ['TIMESTAMP', 'DATETIME']:
        if isinstance(value, str) and value.isdigit():
            return int(value)
    
    return value

def import_table_data_postgresql(conn, table_name, columns, rows):
    """将数据导入到PostgreSQL"""
    if not rows:
        print(f"表 {table_name} 没有数据需要导入")
        return
    
    cursor = conn.cursor()
    
    # 构建INSERT语句
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join([f'"{col}"' for col in columns])
    insert_query = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
    
    # 批量插入数据
    try:
        converted_rows = []
        for row in rows:
            converted_row = []
            for i, value in enumerate(row):
                # 获取列类型信息（简化处理）
                converted_row.append(value)
            converted_rows.append(converted_row)
        
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
        
        # 迁移每个表的数据
        for table_name in tables:
            # 跳过某些系统表
            if table_name in ['sqlite_sequence', 'alembic_version']:
                continue
                
            try:
                migrate_table(conn_sqlite, conn_postgresql, table_name)
            except Exception as e:
                print(f"迁移表 {table_name} 时出错: {e}")
        
        print("数据迁移完成")
        
    except Exception as e:
        print(f"数据迁移过程中出错: {e}")
    finally:
        # 关闭连接
        conn_sqlite.close()
        conn_postgresql.close()

if __name__ == "__main__":
    main()