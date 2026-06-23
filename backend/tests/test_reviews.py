import pytest


@pytest.mark.asyncio
async def test_create_review(client, seed_products, user_token):
    pid = seed_products[0].id
    r = await client.post(
        "/api/reviews",
        json={"product_id": pid, "rating": 5, "text": "Отличный товар!"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["rating"] == 5
    assert data["text"] == "Отличный товар!"


@pytest.mark.asyncio
async def test_create_review_duplicate(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/reviews",
        json={"product_id": pid, "rating": 4, "text": "Хороший"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.post(
        "/api/reviews",
        json={"product_id": pid, "rating": 3, "text": "Ещё один"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_get_reviews(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/reviews",
        json={"product_id": pid, "rating": 4, "text": "Норм"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.get(f"/api/reviews/product/{pid}")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_avg_rating(client, seed_products, user_token):
    pid = seed_products[0].id
    await client.post(
        "/api/reviews",
        json={"product_id": pid, "rating": 4, "text": "ok"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    r = await client.get(f"/api/reviews/product/{pid}/avg")
    assert r.status_code == 200
    data = r.json()
    assert data["avg_rating"] == 4.0
    assert data["review_count"] == 1


@pytest.mark.asyncio
async def test_review_not_found_product(client, user_token):
    r = await client.post(
        "/api/reviews",
        json={"product_id": 99999, "rating": 5, "text": "X"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 404
