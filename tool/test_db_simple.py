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
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')