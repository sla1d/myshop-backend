import pytest


@pytest.mark.asyncio
async def test_add_to_cart(client, seed_products, user_token):
    pid = seed_products[0].id
    r = await client.post(
        "/api/cart/add",
        json={"product_id": pid, "quantity": 2},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_cart(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/cart/add",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.get("/api/cart", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert data["total"] >= seed_products[0].price


@pytest.mark.asyncio
async def test_update_quantity(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/cart/add",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.put(
        f"/api/cart/item/{pid}",
        json={"product_id": pid, "quantity": 5},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200

    cart = await client.get("/api/cart", headers={"Authorization": f"Bearer {user_token}"})
    item = next(i for i in cart.json()["items"] if i["id"] == pid)
    assert item["quantity"] == 5


@pytest.mark.asyncio
async def test_remove_from_cart(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/cart/add",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.delete(
        "/api/cart/remove",
        params={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200

    cart = await client.get("/api/cart", headers={"Authorization": f"Bearer {user_token}"})
    assert cart.json()["count"] == 0


@pytest.mark.asyncio
async def test_clear_cart(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/cart/add",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.delete("/api/cart/clear", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200

    cart = await client.get("/api/cart", headers={"Authorization": f"Bearer {user_token}"})
    assert cart.json()["count"] == 0


@pytest.mark.asyncio
async def test_cart_unauthorized(client):
    r = await client.get("/api/cart")
    assert r.status_code in (401, 403)
