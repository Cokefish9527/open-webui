import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from open_webui.internal.migrations.ugc import ensure_ugc_schema


@pytest.fixture
def sqlite_engine():
    return create_engine("sqlite://")


def test_ensure_ugc_schema_sqlite(sqlite_engine):
    diagnostics = ensure_ugc_schema(sqlite_engine)
    inspector = inspect(sqlite_engine)

    tables = set(inspector.get_table_names())
    assert {
        "hsai_ugc_material_models",
        "hsai_ugc_video_tasks",
        "hsai_ugc_task_scenes",
    }.issubset(tables)

    task_cols = {c["name"] for c in inspector.get_columns("hsai_ugc_video_tasks")}
    assert {"billed_credits", "billed_at", "free_retry_until", "last_trigger_at"}.issubset(
        task_cols
    )

    assert diagnostics["executed"], "expected schema changes to be executed on first run"

    rerun = ensure_ugc_schema(sqlite_engine)
    assert rerun["executed"] == [], "second run should be idempotent"


def test_ensure_ugc_schema_dry_run(sqlite_engine):
    diagnostics = ensure_ugc_schema(sqlite_engine, dry_run=True)
    assert diagnostics["executed"], "dry-run should report planned statements"

    inspector = inspect(sqlite_engine)
    tables = set(inspector.get_table_names())
    assert "hsai_ugc_video_tasks" not in tables, "dry-run must not mutate schema"

