import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_webui.routers import hsai_ugc  # noqa: E402
from open_webui.models.hsai_ugc import ProductData  # noqa: E402
from open_webui.utils.auth import get_verified_user  # noqa: E402


def _build_app(*, user_id: str) -> FastAPI:
    app = FastAPI()
    app.include_router(hsai_ugc.router, prefix="/api/v1")
    app.dependency_overrides[get_verified_user] = lambda: SimpleNamespace(id=user_id)
    return app


def _sample_product(*, product_id: int, user_id: str, name: str = "p1") -> ProductData:
    return ProductData(
        id=product_id,
        user_id=user_id,
        name=name,
        description="d1",
        cover_img="https://example.com/p.png",
        created_at=0,
        updated_at=0,
    )


def test_create_product_ok(monkeypatch):
    def fake_create_product(user_id: str, form):
        assert user_id == "user-1"
        assert form.name == "新品"
        assert form.description == "描述"
        assert form.cover_img == "https://example.com/1.png"
        return _sample_product(product_id=1, user_id=user_id, name=form.name)

    monkeypatch.setattr(hsai_ugc.Products, "create_product", fake_create_product)

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.post(
        "/api/v1/ugc/products",
        json={"name": "新品", "description": "描述", "cover_img": "https://example.com/1.png"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "新品"
    assert "cover_img" in body
    assert "description" in body
    assert "url" not in body
    assert "country" not in body
    assert "language" not in body


def test_create_product_rejects_extra_fields(monkeypatch):
    # If validation works, DAO should never be called.
    monkeypatch.setattr(hsai_ugc.Products, "create_product", lambda *_: (_ for _ in ()).throw(AssertionError("should not call DAO")))

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.post(
        "/api/v1/ugc/products",
        json={
            "name": "新品",
            "description": "描述",
            "cover_img": "https://example.com/1.png",
            "url": "https://example.com/legacy",
        },
    )
    assert resp.status_code == 422


def test_get_products_ok(monkeypatch):
    monkeypatch.setattr(
        hsai_ugc.Products,
        "get_products",
        lambda user_id, q=None, page=1, page_size=20: [
            _sample_product(product_id=1, user_id=user_id),
            _sample_product(product_id=2, user_id=user_id, name="p2"),
        ],
    )

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.get("/api/v1/ugc/products?page=1&page_size=20")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_product_ok(monkeypatch):
    monkeypatch.setattr(hsai_ugc.Products, "get_product", lambda product_id: _sample_product(product_id=product_id, user_id="user-1"))
    monkeypatch.setattr(
        hsai_ugc.Products,
        "update_product",
        lambda product_id, form: _sample_product(product_id=product_id, user_id="user-1", name=form.name or "p1"),
    )

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.put("/api/v1/ugc/products/1", json={"name": "新名字"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名字"


def test_update_product_not_owner_returns_404(monkeypatch):
    monkeypatch.setattr(hsai_ugc.Products, "get_product", lambda product_id: _sample_product(product_id=product_id, user_id="user-1"))

    client = TestClient(_build_app(user_id="user-2"))
    resp = client.put("/api/v1/ugc/products/1", json={"name": "x"})
    assert resp.status_code == 404


def test_delete_product_ok(monkeypatch):
    monkeypatch.setattr(hsai_ugc.Products, "get_product", lambda product_id: _sample_product(product_id=product_id, user_id="user-1"))
    monkeypatch.setattr(hsai_ugc.Products, "delete_product", lambda product_id: True)

    client = TestClient(_build_app(user_id="user-1"))
    resp = client.delete("/api/v1/ugc/products/1")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_delete_product_not_owner_returns_404(monkeypatch):
    monkeypatch.setattr(hsai_ugc.Products, "get_product", lambda product_id: _sample_product(product_id=product_id, user_id="user-1"))

    client = TestClient(_build_app(user_id="user-2"))
    resp = client.delete("/api/v1/ugc/products/1")
    assert resp.status_code == 404

