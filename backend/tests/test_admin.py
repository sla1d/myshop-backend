import pytest


@pytest.mark.asyncio
async def test_admin_stats(client, seed_admin, seed_products, admin_token):
    r = await client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_products"] == 4
    assert data["total_users"] >= 1


@pytest.mark.asyncio
async def test_admin_get_users(client, seed_admin, seed_user, admin_token):
    r = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) >= 2


@pytest.mark.asyncio
async def admin_change_user_role(client, seed_admin, seed_user, admin_token):
    r = await client.patch(
        f"/api/admin/users/{seed_user.id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_admin_create_product(client, seed_admin, admin_token):
    r = await client.post(
        "/api/admin/products",
        json={
            "name": "Тестовый товар",
            "price": 999,
            "image": "https://picsum.photos/seed/test/300/300",
            "category": "test",
            "brand": "TestBrand",
            "rating": 4.0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Тестовый товар"


@pytest.mark.asyncio
async def test_admin_update_product(client, seed_products, seed_admin, admin_token):
    pid = seed_products[0].id
    r = await client.put(
        f"/api/admin/products/{pid}",
        json={
            "name": "Обновлённый",
            "price": 11111,
            "image": "img.jpg",
            "category": "test",
            "brand": "Test",
            "rating": 4.0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Обновлённый"


@pytest.mark.asyncio
async def test_admin_delete_product(client, seed_products, seed_admin, admin_token):
    pid = seed_products[3].id
    r = await client.delete(
        f"/api/admin/products/{pid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_only(client, seed_products, user_token):
    r = await client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_unauthorized(client):
    r = await client.get("/api/admin/stats")
    assert r.status_code in (401, 403)
