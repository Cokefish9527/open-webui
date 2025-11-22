#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为战略蓝图进度表添加info_collection_processed字段
"""

import os
import sys

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))


def add_info_collection_processed_column():
    from sqlalchemy import create_engine, text
    
    # 直接使用数据库URL，避免加载环境变量
    DATABASE_URL = "postgresql://hsai:c5agLR%29ah28vnA3+%25Yyn@pgm-bp1x8d937cl58d1afo.pg.rds.aliyuncs.com:5432/Owen_ai"

    if "postgresql" not in DATABASE_URL.lower():
        print("本脚本当前仅支持 PostgreSQL 数据库。")
        return False

    engine = create_engine(DATABASE_URL)

    # 添加info_collection_processed字段到hsai_blueprint_progress表
    alter_table_sql = """
    ALTER TABLE hsai_blueprint_progress 
    ADD COLUMN IF NOT EXISTS info_collection_processed BOOLEAN DEFAULT FALSE NOT NULL
    """

    print("开始添加info_collection_processed字段到hsai_blueprint_progress表...")

    try:
        with engine.begin() as conn:
            conn.execute(text(alter_table_sql))
        print("字段添加成功。")
        return True
    except Exception as e:
        print(f"添加字段时发生错误: {e}")
        return False


def main():
    print("== 战略蓝图进度表添加info_collection_processed字段 ==")
    success = add_info_collection_processed_column()
    if success:
        print("✅ info_collection_processed字段添加完成。")
        return 0

    print("❌ info_collection_processed字段添加失败。")
    return 1


if __name__ == "__main__":
    sys.exit(main())