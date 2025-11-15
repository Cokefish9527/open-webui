import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from open_webui.internal.migrations import ensure_materials_storage_schema  # noqa: E402
from open_webui.models import hsai_materials  # noqa: E402


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


def test_schema_guard_invokes_migration_once(monkeypatch):
    calls = []

    class DummySession:
        def __init__(self):
            self._bind = object()

        def get_bind(self):
            return self._bind

    @contextmanager
    def fake_get_db():
        yield DummySession()

    def fake_ensure(bind, *, schema, logger):
        calls.append((bind, schema))

    monkeypatch.setattr(hsai_materials, "get_db", fake_get_db)
    monkeypatch.setattr(hsai_materials, "ensure_materials_storage_schema", fake_ensure)
    hsai_materials._SCHEMA_READY = False

    with hsai_materials._schema_aware_db():
        pass
    with hsai_materials._schema_aware_db():
        pass

    assert calls and calls[0][1] == hsai_materials.DATABASE_SCHEMA
    assert len(calls) == 1, "second invocation should use cached schema guard"

    hsai_materials._SCHEMA_READY = False


def test_get_materials_by_user_id_uses_schema_guard(monkeypatch):
    guard_calls = {"entered": 0}

    class DummyQuery:
        def filter_by(self, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def offset(self, *args, **kwargs):
            return self

        def all(self):
            return []

    class DummySession:
        def query(self, model):
            return DummyQuery()

    @contextmanager
    def fake_schema_db():
        guard_calls["entered"] += 1
        yield DummySession()

    monkeypatch.setattr(hsai_materials, "_schema_aware_db", fake_schema_db)

    table = hsai_materials.HSAIMaterialsTable()
    materials = table.get_materials_by_user_id("user-123")

    assert materials == [], "dummy query should return empty list"
    assert guard_calls["entered"] == 1, "schema guard context should wrap DB access"
