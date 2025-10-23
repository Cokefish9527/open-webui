#!/usr/bin/env python3
"""
为 credit / credit_log 表补充 company_id 列，并将现有数据回填所属公司。
"""

import os
import sys

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text


def _column_exists(connection, table: str, column: str, dialect: str) -> bool:
    if "postgresql" in dialect:
        query = """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table AND column_name = :column
        LIMIT 1
        """
        result = connection.execute(
            text(query), {"table": table, "column": column}
        )
        return result.scalar() is not None

    # SQLite
    result = connection.execute(text(f"PRAGMA table_info('{table}')"))
    return any(row[1] == column for row in result.fetchall())


def _add_column(connection, table: str, column_def: str, dialect: str) -> None:
    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
    connection.commit()


def _update_credit_company_id(connection, dialect: str) -> None:
    """
    基于 user.company_id 回填 credit/company_id 与 credit_log.company_id。
    """
    if "postgresql" in dialect:
        connection.execute(
            text(
                """
                UPDATE credit AS c
                SET company_id = u.company_id
                FROM "user" AS u
                WHERE c.user_id = u.id
                  AND u.company_id IS NOT NULL
                  AND (c.company_id IS NULL OR c.company_id <> u.company_id)
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE credit_log AS cl
                SET company_id = COALESCE(cl.company_id, c.company_id, u.company_id)
                FROM credit AS c
                LEFT JOIN "user" AS u ON u.id = cl.user_id
                WHERE cl.user_id = c.user_id
                  AND cl.company_id IS NULL
                """
            )
        )
        connection.commit()
    else:
        # SQLite 不支持 UPDATE ... FROM，拆成多条语句
        connection.execute(
            text(
                """
                UPDATE credit
                SET company_id = (
                    SELECT company_id FROM "user"
                    WHERE "user".id = credit.user_id
                )
                WHERE company_id IS NULL
                  AND EXISTS (
                      SELECT 1 FROM "user"
                      WHERE "user".id = credit.user_id
                        AND "user".company_id IS NOT NULL
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE credit_log
                SET company_id = (
                    SELECT COALESCE(credit.company_id, "user".company_id)
                    FROM credit
                    LEFT JOIN "user" ON "user".id = credit_log.user_id
                    WHERE credit.user_id = credit_log.user_id
                    LIMIT 1
                )
                WHERE company_id IS NULL
                """
            )
        )
        connection.commit()


def migrate() -> int:
    try:
        from open_webui.env import DATABASE_URL
        from sqlalchemy import create_engine, text

        engine = create_engine(DATABASE_URL)
        dialect = engine.dialect.name.lower()

        print(f"数据库 URL: {DATABASE_URL}")
        print("开始检查 credit / credit_log 的 company_id 列…")

        with engine.connect() as connection:
            needs_commit = False

            if not _column_exists(connection, "credit", "company_id", dialect):
                print("➕ credit 表缺失 company_id，正在添加…")
                column_def = (
                    "company_id VARCHAR(255)"
                    if "postgresql" in dialect
                    else "company_id TEXT"
                )
                _add_column(connection, "credit", column_def, dialect)
                needs_commit = True
            else:
                print("credit 表已存在 company_id")

            if not _column_exists(connection, "credit_log", "company_id", dialect):
                print("➕ credit_log 表缺失 company_id，正在添加…")
                column_def = (
                    "company_id VARCHAR(255)"
                    if "postgresql" in dialect
                    else "company_id TEXT"
                )
                _add_column(connection, "credit_log", column_def, dialect)
                needs_commit = True
            else:
                print("credit_log 表已存在 company_id")

            if needs_commit:
                print("列添加完成，开始回填历史数据…")
            else:
                print("列已存在，直接校验并回填历史数据…")

            _update_credit_company_id(connection, dialect)

        print("✅ 迁移完成")
        return 0
    except Exception as exc:  # pragma: no cover - 调试输出
        import traceback

        print(f"❌ 迁移失败: {exc}")
        traceback.print_exc()
        return 1


def main():
    print("=== 公司积分列补全脚本 ===")
    sys.exit(migrate())


if __name__ == "__main__":
    main()
