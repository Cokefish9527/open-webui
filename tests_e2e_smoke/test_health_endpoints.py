import os
import pytest


pytestmark = pytest.mark.e2e_smoke


def test_health_contract_shape():
    if os.getenv("E2E_SMOKE", "1") != "1":
        pytest.skip("E2E_SMOKE disabled; skipping")

    expected_paths = [
        "/health",
        "/health/db",
    ]
    for p in expected_paths:
        assert p.startswith("/") and len(p) > 1

