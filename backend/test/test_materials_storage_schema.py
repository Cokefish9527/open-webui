import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from open_webui.internal.migrations import ensure_materials_storage_schema  # noqa: E402


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE hsai_materials (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL
                )
                """
            )
        )
    return engine


def test_ensure_materials_storage_schema_sqlite(sqlite_engine):
    diagnostics = ensure_materials_storage_schema(sqlite_engine)
    inspector = inspect(sqlite_engine)

    columns = {column["name"] for column in inspector.get_columns("hsai_materials")}
    assert {"oss_bucket", "oss_key", "oss_object_path"}.issubset(columns)
    assert diagnostics["executed"], "expected schema alterations on first invocation"

    rerun = ensure_materials_storage_schema(sqlite_engine)
    assert not rerun["executed"], "second run should be idempotent"


def test_ensure_materials_storage_schema_dry_run(sqlite_engine):
    diagnostics = ensure_materials_storage_schema(sqlite_engine, dry_run=True)
    assert diagnostics["executed"], "dry-run should list planned statements"

    inspector = inspect(sqlite_engine)
    columns = {column["name"] for column in inspector.get_columns("hsai_materials")}
    assert "oss_object_path" not in columns, "dry-run must not mutate schema"
