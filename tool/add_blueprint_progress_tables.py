#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建战略蓝图进度相关数据表:
- hsai_blueprint_progress
- hsai_blueprint_progress_history
- hsai_task_blueprint_links
"""

import os
import sys

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))


def create_tables():
    from sqlalchemy import create_engine, text
    from open_webui.env import DATABASE_URL

    if "postgresql" not in DATABASE_URL.lower():
        print("本脚本当前仅支持 PostgreSQL 数据库。")
        return False

    engine = create_engine(DATABASE_URL)

    create_progress_sql = """
    CREATE TABLE IF NOT EXISTS hsai_blueprint_progress (
        id VARCHAR PRIMARY KEY,
        project_id VARCHAR NOT NULL REFERENCES hsai_projects(id),
        blueprint_version VARCHAR NOT NULL,
        execution_duration_days VARCHAR,
        planned_total_posts VARCHAR,
        posting_frequency VARCHAR,
        required_tiktok_accounts VARCHAR,
        summary_md TEXT,
        blueprint_raw TEXT,
        latest_digest JSONB,
        progress_state VARCHAR NOT NULL DEFAULT 'planning',
        daily_cycle_config JSONB,
        last_synced_at BIGINT NOT NULL,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        CONSTRAINT uq_hsai_blueprint_progress_project UNIQUE (project_id)
    )
    """

    create_history_sql = """
    CREATE TABLE IF NOT EXISTS hsai_blueprint_progress_history (
        id VARCHAR PRIMARY KEY,
        progress_id VARCHAR NOT NULL REFERENCES hsai_blueprint_progress(id) ON DELETE CASCADE,
        operation VARCHAR NOT NULL,
        operator_id VARCHAR,
        changes_json JSONB,
        snapshot_md TEXT,
        created_at BIGINT NOT NULL
    )
    """

    create_links_sql = """
    CREATE TABLE IF NOT EXISTS hsai_task_blueprint_links (
        id VARCHAR PRIMARY KEY,
        progress_id VARCHAR NOT NULL REFERENCES hsai_blueprint_progress(id) ON DELETE CASCADE,
        task_id VARCHAR NOT NULL REFERENCES hsai_tasks(id) ON DELETE CASCADE,
        template_key VARCHAR NOT NULL,
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL,
        CONSTRAINT uq_blueprint_task_template UNIQUE (progress_id, template_key)
    )
    """

    print("开始创建战略蓝图进度相关表...")

    with engine.begin() as conn:
        conn.execute(text(create_progress_sql))
        conn.execute(text(create_history_sql))
        conn.execute(text(create_links_sql))

    print("表结构检查完成。")
    return True


def main():
    print("== 战略蓝图进度表初始化 ==")
    success = create_tables()
    if success:
        print("✅ 蓝图进度表及关联表准备完成。")
        return 0

    print("❌ 蓝图进度表初始化失败。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
