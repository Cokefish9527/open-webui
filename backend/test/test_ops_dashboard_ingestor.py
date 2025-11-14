import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from open_webui.services import ops_dashboard_ingestor as ingestor


async def _wait_until(predicate, timeout: float = 1.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("timeout waiting for predicate")


def test_dispatcher_processes_events(monkeypatch):
    async def _run():
        processed = []

        async def fake_record(message):
            processed.append(message)
            return True

        monkeypatch.setattr(ingestor, "_record_conversation_event", fake_record)
        monkeypatch.setattr(ingestor, "OPS_DASHBOARD_ENABLED", True)

        await ingestor.stop_conversation_ingestion()
        await ingestor.start_conversation_ingestion()

        ingestor.enqueue_conversation_event({"session_id": "sess-1"})
        await _wait_until(lambda: len(processed) == 1)

        await ingestor.stop_conversation_ingestion()
        assert processed[0]["session_id"] == "sess-1"

    asyncio.run(_run())


def test_dispatcher_drains_queue_on_stop(monkeypatch):
    async def _run():
        processed = []

        async def slow_record(message):
            processed.append(message["session_id"])
            await asyncio.sleep(0.05)
            return True

        monkeypatch.setattr(ingestor, "_record_conversation_event", slow_record)
        monkeypatch.setattr(ingestor, "OPS_DASHBOARD_ENABLED", True)

        await ingestor.stop_conversation_ingestion()
        await ingestor.start_conversation_ingestion()

        for idx in range(3):
            ingestor.enqueue_conversation_event({"session_id": f"sess-{idx}"})

        await ingestor.stop_conversation_ingestion()
        assert processed == ["sess-0", "sess-1", "sess-2"]

    asyncio.run(_run())
