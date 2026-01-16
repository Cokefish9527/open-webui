import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_webui.routers import hsai_ugc  # noqa: E402
from open_webui.models.hsai_ugc import MaterialModelData  # noqa: E402
from open_webui.utils.auth import get_verified_user  # noqa: E402


def _build_app(*, user_id: str) -> FastAPI:
    app = FastAPI()
    app.include_router(hsai_ugc.router, prefix="/api/v1")
    app.dependency_overrides[get_verified_user] = lambda: SimpleNamespace(id=user_id)
    return app


def _sample_model(*, model_id: int, user_id: str) -> MaterialModelData:
    return MaterialModelData(
        id=model_id,
        user_id=user_id,
        model_name="m1",
        model_img_url="https://example.com/m.png",
        voice_provider_id="v1",
        voice_preview_url="https://example.com/v.wav",
        created_at=0,
    )


def test_get_model_detail_ok(monkeypatch):
    def fake_get_model_by_id_and_user_id(model_id: int, user_id: str):
        assert model_id == 1
        assert user_id == "user-1"
        return _sample_model(model_id=model_id, user_id=user_id)

    monkeypatch.setattr(hsai_ugc.MaterialModels, "get_model_by_id_and_user_id", fake_get_model_by_id_and_user_id)

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.get("/api/v1/ugc/models/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_get_model_detail_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(hsai_ugc.MaterialModels, "get_model_by_id_and_user_id", lambda *_: None)

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.get("/api/v1/ugc/models/999")
    assert resp.status_code == 404

