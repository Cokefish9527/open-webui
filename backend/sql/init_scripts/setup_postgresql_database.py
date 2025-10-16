import psycopg2
from psycopg2 import sql
import os

# PostgreSQL数据库连接配置
DB_HOST = "pgm-bp1x8d937cl58d1afo.pg.rds.aliyuncs.com"
DB_PORT = "5432"
DB_USER = "hsai"
DB_PASSWORD = "c5agLR)ah28vnA3+%Yyn"
DB_NAME = "Owen_ai"

def create_database():
    """创建Owen_ai数据库"""
    # 先连接到默认的postgres数据库
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database="postgres"  # 连接到默认数据库
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # 检查数据库是否已存在
    cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
    exists = cursor.fetchone()
    
    if not exists:
        # 创建数据库
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        print(f"数据库 {DB_NAME} 创建成功")
    else:
        print(f"数据库 {DB_NAME} 已存在")
    
    cursor.close()
    conn.close()

def initialize_database():
    """初始化数据库表结构"""
    # 连接到Owen_ai数据库
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # 读取PostgreSQL完整数据库初始化脚本
    script_path = os.path.join(os.path.dirname(__file__), "postgresql_full_database_init_v4.sql")
    
    with open(script_path, 'r', encoding='utf-8') as file:
        sql_script = file.read()
    
    # 执行SQL脚本
    try:
        cursor.execute(sql_script)
        conn.commit()
        print("数据库表结构初始化成功")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        conn.rollback()
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        create_database()
        initialize_database()
        print("PostgreSQL数据库Owen_ai设置完成")
    except Exception as e:
        print(f"设置过程中出现错误: {e}")