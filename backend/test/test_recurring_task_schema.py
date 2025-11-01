import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from open_webui.internal.migrations import ensure_recurring_task_schema


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE hsai_tasks (
                    id VARCHAR PRIMARY KEY,
                    title VARCHAR NOT NULL
                )
                """
            )
        )
    return engine


def test_ensure_recurring_task_schema_sqlite(sqlite_engine):
    diagnostics = ensure_recurring_task_schema(sqlite_engine)
    inspector = inspect(sqlite_engine)

    task_columns = {column["name"] for column in inspector.get_columns("hsai_tasks")}
    assert {"is_recurring", "recurring_state", "last_run_at", "next_run_at"}.issubset(task_columns)
    assert {"external_controller", "recurring_meta"}.issubset(task_columns)

    tables = set(inspector.get_table_names())
    assert "hsai_task_state_logs" in tables

    task_indexes = {index["name"] for index in inspector.get_indexes("hsai_tasks")}
    log_indexes = {index["name"] for index in inspector.get_indexes("hsai_task_state_logs")}

    assert "idx_hsai_tasks_recurring_state" in task_indexes
    assert "idx_hsai_task_state_logs_task" in log_indexes
    assert diagnostics["executed"], "expected schema changes to be executed on first run"

    rerun = ensure_recurring_task_schema(sqlite_engine)
    assert rerun["executed"] == [], "second run should be idempotent"


def test_ensure_recurring_task_schema_dry_run(sqlite_engine):
    diagnostics = ensure_recurring_task_schema(sqlite_engine, dry_run=True)
    assert diagnostics["executed"], "dry-run should report planned statements"

    inspector = inspect(sqlite_engine)
    task_columns = {column["name"] for column in inspector.get_columns("hsai_tasks")}
    assert "is_recurring" not in task_columns, "dry-run must not mutate schema"
