import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from open_webui.internal.migrations import ensure_coupon_schema


@pytest.fixture
def sqlite_engine():
    return create_engine("sqlite://")


def test_ensure_coupon_schema_sqlite(sqlite_engine):
    diagnostics = ensure_coupon_schema(sqlite_engine)
    inspector = inspect(sqlite_engine)

    tables = set(inspector.get_table_names())
    assert {"hsai_coupon_batches", "hsai_coupons", "hsai_coupon_redeem_txns"}.issubset(tables)

    coupon_columns = {c["name"] for c in inspector.get_columns("hsai_coupons")}
    assert {"code", "status", "face_value", "expires_at"}.issubset(coupon_columns)

    indexes = {i["name"] for i in inspector.get_indexes("hsai_coupons")}
    assert "idx_hsai_coupons_code" in indexes
    assert diagnostics["executed"], "expected schema changes to be executed on first run"

    rerun = ensure_coupon_schema(sqlite_engine)
    assert rerun["executed"] == [], "second run should be idempotent"


def test_ensure_coupon_schema_dry_run(sqlite_engine):
    diagnostics = ensure_coupon_schema(sqlite_engine, dry_run=True)
    assert diagnostics["executed"], "dry-run should report planned statements"

    inspector = inspect(sqlite_engine)
    tables = set(inspector.get_table_names())
    assert "hsai_coupons" not in tables, "dry-run must not mutate schema"

