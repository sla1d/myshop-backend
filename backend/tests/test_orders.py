import pytest


@pytest.mark.asyncio
async def test_create_order(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/cart/add",
        json={"product_id": pid, "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.post(
        "/api/order",
        json={"address": "Москва, ул. Тестовая, 1"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "order_id" in data
    assert data["total"] >= seed_products[0].price


@pytest.mark.asyncio
async def test_create_order_empty_cart(client, user_token):
    r = await client.post(
        "/api/order",
        json={"address": "Москва"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_order_with_promo(client, seed_products, seed_promo, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/cart/add",
        json={"product_id": pid, "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.post(
        "/api/order",
        json={"address": "Москва", "promo_code": "TEST20"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    assert r.json()["total"] < seed_products[0].price


@pytest.mark.asyncio
async def test_order_unauthorized(client):
    r = await client.post("/api/order", json={"address": "Test"})
    assert r.status_code in (401, 403)
