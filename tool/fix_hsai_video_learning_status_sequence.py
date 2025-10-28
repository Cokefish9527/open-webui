#!/usr/bin/env python3
"""
视频学习状态表结构与序列修复脚本
- 校验 business_name + video_id 是否存在重复
- 为 PostgreSQL/SQLite 添加联合唯一约束（或唯一索引）与检索索引
- 重置自增序列，避免再次出现 duplicate key

使用方式：
    python tool/fix_hsai_video_learning_status_sequence.py             # 仅检测（dry-run）
    python tool/fix_hsai_video_learning_status_sequence.py --apply     # 实际执行修复
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from open_webui.env import DATABASE_URL


def _log(msg: str) -> None:
    print(f"[hsai_video_learning_status] {msg}")


def _detect_duplicates(engine: Engine) -> List[Tuple[str, str, int]]:
    dup_sql = text(
        """
        SELECT business_name, video_id, COUNT(*) AS cnt
        FROM hsai_video_learning_status
        GROUP BY business_name, video_id
        HAVING COUNT(*) > 1
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(dup_sql).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def _ensure_postgres_constraints(engine: Engine, apply: bool) -> None:
    with engine.begin() as conn:
        # 添加联合唯一约束
        constraint_exists = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'uq_hsai_video_learning_status_business_video'
                  AND table_name = 'hsai_video_learning_status'
                """
            )
        ).fetchone()
        if constraint_exists:
            _log("检测到联合唯一约束已存在，跳过创建。")
        else:
            if not apply:
                _log("[dry-run] 将创建联合唯一约束 uq_hsai_video_learning_status_business_video。")
            else:
                _log("创建联合唯一约束 uq_hsai_video_learning_status_business_video ...")
                conn.execute(
                    text(
                        """
                        ALTER TABLE hsai_video_learning_status
                        ADD CONSTRAINT uq_hsai_video_learning_status_business_video
                        UNIQUE (business_name, video_id)
                        """
                    )
                )

        # 添加业务索引
        _log("确保存在 business_name + status 索引 ...")
        if apply:
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_status_business_status
                    ON hsai_video_learning_status (business_name, status)
                    """
                )
            )
        else:
            _log("[dry-run] 将执行 CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_status_business_status ...")

        # 重置序列
        seq_name = conn.execute(
            text("SELECT pg_get_serial_sequence('hsai_video_learning_status', 'id')")
        ).scalar()
        if seq_name:
            if apply:
                _log(f"重置序列 {seq_name} ...")
                conn.execute(
                    text(
                        f"SELECT setval('{seq_name}', (SELECT COALESCE(MAX(id), 1) FROM hsai_video_learning_status))"
                    )
                )
            else:
                _log(f"[dry-run] 将重置序列 {seq_name} 至当前最大 id。")
        else:
            _log("警告：未能获取 id 序列名称，请确认表结构。")


def _ensure_sqlite_constraints(engine: Engine, apply: bool) -> None:
    with engine.begin() as conn:
        # 创建唯一索引（SQLite 无法直接新增联合约束，改用唯一索引实现）
        if apply:
            _log("创建（或确认存在）联合唯一索引 uq_hsai_video_learning_status_business_video ...")
            conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_hsai_video_learning_status_business_video
                    ON hsai_video_learning_status (business_name, video_id)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_hsai_video_learning_status_business_status
                    ON hsai_video_learning_status (business_name, status)
                    """
                )
            )
        else:
            _log("[dry-run] 将创建联合唯一索引及 status 索引。")

        # 重置 AUTOINCREMENT 序列
        if apply:
            _log("重置 sqlite_sequence 中的 id 序列 ...")
            conn.execute(
                text(
                    """
                    INSERT INTO sqlite_sequence (name, seq)
                    VALUES ('hsai_video_learning_status', (SELECT COALESCE(MAX(id), 0) FROM hsai_video_learning_status))
                    ON CONFLICT(name) DO UPDATE SET seq = excluded.seq
                    """
                )
            )
        else:
            _log("[dry-run] 将更新 sqlite_sequence 使其与当前最大 id 保持一致。")


def main() -> int:
    parser = argparse.ArgumentParser(description="修复 hsai_video_learning_status 表结构与序列。")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际执行修复操作（默认仅检测，不写入）。",
    )
    args = parser.parse_args()

    if not DATABASE_URL:
        _log("错误：未配置 DATABASE_URL，无法连接数据库。")
        return 2

    engine = create_engine(DATABASE_URL)

    try:
        duplicates = _detect_duplicates(engine)
        if duplicates:
            _log("发现重复数据（business_name, video_id, count）：")
            for business_name, video_id, count in duplicates:
                _log(f"  - {business_name} | {video_id} | {count}")
            _log("请先清理重复记录后再执行修复。")
            return 1
        else:
            _log("未检测到重复的 (business_name, video_id) 记录。")

        lowered = DATABASE_URL.lower()
        if "postgres" in lowered:
            _log("检测到 PostgreSQL 数据库。")
            _ensure_postgres_constraints(engine, apply=args.apply)
        elif "sqlite" in lowered:
            _log("检测到 SQLite 数据库。")
            _ensure_sqlite_constraints(engine, apply=args.apply)
        else:
            _log(f"暂不支持的数据库类型：{DATABASE_URL}")
            return 3

        if args.apply:
            _log("修复流程执行完成。")
        else:
            _log("检测完成（dry-run）。若需实际写入，请添加 --apply 参数。")
        return 0

    except SQLAlchemyError as exc:
        _log(f"执行过程中发生数据库异常：{exc}")
        return 4
    except Exception as exc:  # pragma: no cover
        _log(f"执行过程中发生未知异常：{exc}")
        return 5
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
