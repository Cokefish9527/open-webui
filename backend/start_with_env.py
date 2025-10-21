import os
import sys

# 设置数据库URL环境变量（默认指向 PostgreSQL，若外部已设置则不覆盖）
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://hsai:c5agLR%29ah28vnA3+%25Yyn@pgm-bp1x8d937cl58d1afo.pg.rds.aliyuncs.com:5432/Owen_ai",
)

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并运行uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "open_webui.main:app",
        host="0.0.0.0",
        port=8080,
        forwarded_allow_ips="*",
        workers=1,
        ws="auto",
    )
