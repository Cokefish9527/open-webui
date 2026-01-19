import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_webui.routers import external_admin_minimax  # noqa: E402


def _build_app():
    app = FastAPI()
    # Match production mounting: main.py mounts with prefix="/api/v1"
    app.include_router(external_admin_minimax.router, prefix="/api/v1")
    return app


@pytest.fixture()
def client(monkeypatch):
    async def fake_verify(_request):
        return {"authenticated": True, "client_id": "test"}

    monkeypatch.setattr(external_admin_minimax, "verify_external_request", fake_verify)
    return TestClient(_build_app())


def _dummy_account(
    *,
    id: int = 1,
    name: str = "acc-1",
    enabled: bool = True,
    is_default: bool = True,
    api_key: str = "sk_test_1234567890",
    group_id: str = "group-1",
):
    now = datetime.now(tz=timezone.utc)
    return SimpleNamespace(
        id=id,
        name=name,
        enabled=enabled,
        is_default=is_default,
        api_key=api_key,
        group_id=group_id,
        meta_json=None,
        created_at=now,
        updated_at=now,
    )


def test_accounts_list_masks_api_key(monkeypatch, client):
    monkeypatch.setattr(external_admin_minimax.MiniMaxAccounts, "list_accounts", lambda: [_dummy_account()])

    resp = client.get("/api/v1/external/admin/minimax/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["has_api_key"] is True
    assert "****" in data[0]["api_key_masked"]
    assert data[0]["api_key_masked"].endswith("7890")
    assert "api_key" not in data[0]


def test_accounts_create_does_not_echo_api_key(monkeypatch, client):
    monkeypatch.setattr(
        external_admin_minimax.MiniMaxAccounts,
        "create_account",
        lambda **kwargs: _dummy_account(id=2, name=kwargs["name"], is_default=kwargs.get("is_default", False)),
    )
    resp = client.post(
        "/api/v1/external/admin/minimax/accounts",
        json={"name": "new", "api_key": "secret", "group_id": "g1", "enabled": True, "is_default": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "new"
    assert "api_key" not in body


def test_get_voices_calls_upstream(monkeypatch, client):
    monkeypatch.setattr(external_admin_minimax.MiniMaxAccounts, "get_account", lambda _id: _dummy_account(id=_id))

    captured = {}

    async def fake_get_voice(*, api_key: str, voice_type: str):
        captured["api_key"] = api_key
        captured["voice_type"] = voice_type
        return {"data": {"voice_list": []}, "base_resp": {"status_code": 0}}

    monkeypatch.setattr(external_admin_minimax.minimax_speech_client, "get_voice", fake_get_voice)

    resp = client.post(
        "/api/v1/external/admin/minimax/accounts/1/voices",
        json={"voice_type": "system"},
    )
    assert resp.status_code == 200
    assert captured["voice_type"] == "system"


def test_t2a_persist_uploads_and_returns_audio_url(monkeypatch, client):
    monkeypatch.setattr(external_admin_minimax.MiniMaxAccounts, "get_account", lambda _id: _dummy_account(id=_id))

    async def fake_t2a_v2(*, api_key: str, payload):
        # hex "00 01" -> 2 bytes
        assert payload.get("output_format") == "hex"
        return {"data": {"audio": "0001"}, "base_resp": {"status_code": 0}}

    monkeypatch.setattr(external_admin_minimax.minimax_speech_client, "t2a_v2", fake_t2a_v2)
    monkeypatch.setattr(external_admin_minimax.Storage, "upload_file", lambda *_args, **_kwargs: (b"", "s3://bucket/a.wav"))
    monkeypatch.setattr(external_admin_minimax.Storage, "generate_download_url", lambda *_args, **_kwargs: "http://example.com/a.wav")

    resp = client.post(
        "/api/v1/external/admin/minimax/accounts/1/speech/t2a",
        json={"model": "speech-02-turbo", "text": "hi", "voice_id": "male", "persist": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["audio_url"] == "http://example.com/a.wav"
    assert "audio" not in body["data"]
