import sqlite3

# 连接到数据库
conn = sqlite3.connect('data/webui.db')
cursor = conn.cursor()

# 获取user表的结构信息
cursor.execute('PRAGMA table_info(user)')
columns = cursor.fetchall()

print("User table columns:")
for col in columns:
    print(col)

# 检查是否有company_id列
has_company_id = any(col[1] == 'company_id' for col in columns)
print(f"\nHas company_id column: {has_company_id}")

# 获取companies表的结构信息
try:
    cursor.execute('PRAGMA table_info(companies)')
    columns = cursor.fetchall()
    print("\nCompanies table columns:")
    for col in columns:
        print(col)
except Exception as e:
    print(f"\nError getting companies table info: {e}")

# 获取hsai_projects表的结构信息
try:
    cursor.execute('PRAGMA table_info(hsai_projects)')
    columns = cursor.fetchall()
    print("\nHSAI Projects table columns:")
    for col in columns:
        print(col)
        
    # 检查是否有company_id列
    has_company_id = any(col[1] == 'company_id' for col in columns)
    print(f"\nHSAI Projects table has company_id column: {has_company_id}")
except Exception as e:
    print(f"\nError getting hsai_projects table info: {e}")

# 获取hsai_tasks表的结构信息
try:
    cursor.execute('PRAGMA table_info(hsai_tasks)')
    columns = cursor.fetchall()
    print("\nHSAI Tasks table columns:")
    for col in columns:
        print(col)
        
    # 检查是否有project_id列
    has_project_id = any(col[1] == 'project_id' for col in columns)
    print(f"\nHSAI Tasks table has project_id column: {has_project_id}")
    
    # 检查是否有task_category列
    has_task_category = any(col[1] == 'task_category' for col in columns)
    print(f"\nHSAI Tasks table has task_category column: {has_task_category}")
    
    # 检查是否有prompt_config列
    has_prompt_config = any(col[1] == 'prompt_config' for col in columns)
    print(f"\nHSAI Tasks table has prompt_config column: {has_prompt_config}")
except Exception as e:
    print(f"\nError getting hsai_tasks table info: {e}")

conn.close()