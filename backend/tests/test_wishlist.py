import pytest


@pytest.mark.asyncio
async def test_add_to_wishlist(client, seed_products, user_token):
    pid = seed_products[0].id
    r = await client.post(
        "/api/wishlist",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_add_to_wishlist_duplicate(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/wishlist",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.post(
        "/api/wishlist",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "already_exists"


@pytest.mark.asyncio
async def test_get_wishlist(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/wishlist",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.get("/api/wishlist", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["product_id"] == pid


@pytest.mark.asyncio
async def test_remove_from_wishlist(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/wishlist",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.delete(
        f"/api/wishlist/{pid}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200

    wl = await client.get("/api/wishlist", headers={"Authorization": f"Bearer {user_token}"})
    assert len(wl.json()) == 0


@pytest.mark.asyncio
async def test_check_wishlist(client, seed_products, user_token):
    pid = seed_products[0].id
    r = await client.get(
        f"/api/wishlist/check/{pid}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    assert r.json()["is_wishlisted"] is False

    await client.post(
        "/api/wishlist",
        json={"product_id": pid},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.get(
        f"/api/wishlist/check/{pid}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.json()["is_wishlisted"] is True
