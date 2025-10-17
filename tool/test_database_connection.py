import os
import psycopg2
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('d:/Work/hsch/open-webui/.env')

# 获取数据库URL
db_url = os.getenv('DATABASE_URL')
print('Connecting to:', db_url)

try:
    # 连接数据库
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # 执行查询
    cursor.execute('SELECT version()')
    version = cursor.fetchone()
    if version:
        print('PostgreSQL version:', version[0])
    else:
        print('Failed to get PostgreSQL version')
    
    # 查询用户表
    cursor.execute('SELECT COUNT(*) FROM "user"')
    user_count_result = cursor.fetchone()
    user_count = user_count_result[0] if user_count_result else 0
    print(f'用户表记录数: {user_count}')
    
    # 查询公司表
    cursor.execute('SELECT COUNT(*) FROM companies')
    company_count_result = cursor.fetchone()
    company_count = company_count_result[0] if company_count_result else 0
    print(f'公司表记录数: {company_count}')
    
    # 查询项目表
    cursor.execute('SELECT COUNT(*) FROM hsai_projects')
    project_count_result = cursor.fetchone()
    project_count = project_count_result[0] if project_count_result else 0
    print(f'项目表记录数: {project_count}')
    
    # 关闭连接
    cursor.close()
    conn.close()
    print('Database connection successful')
    
except Exception as e:
    print(f'Database connection failed: {e}')