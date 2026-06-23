import pytest


@pytest.mark.asyncio
async def test_get_products(client, seed_products):
    r = await client.get("/api/products")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4


@pytest.mark.asyncio
async def test_get_products_search(client, seed_products):
    r = await client.get("/api/products", params={"search": "Смартфон"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Смартфон X"


@pytest.mark.asyncio
async def test_get_products_filter_category(client, seed_products):
    r = await client.get("/api/products", params={"category": "electronics"})
    assert r.status_code == 200
    assert len(r.json()) == 4


@pytest.mark.asyncio
async def test_get_products_filter_brand(client, seed_products):
    r = await client.get("/api/products", params={"brand": "TechCo"})
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_get_products_price_filter(client, seed_products):
    r = await client.get("/api/products", params={"min_price": 20000, "max_price": 50000})
    assert r.status_code == 200
    assert all(20000 <= p["price"] <= 50000 for p in r.json())


@pytest.mark.asyncio
async def test_get_products_sort_price_asc(client, seed_products):
    r = await client.get("/api/products", params={"sort": "price_asc"})
    assert r.status_code == 200
    prices = [p["price"] for p in r.json()]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_get_products_sort_price_desc(client, seed_products):
    r = await client.get("/api/products", params={"sort": "price_desc"})
    assert r.status_code == 200
    prices = [p["price"] for p in r.json()]
    assert prices == sorted(prices, reverse=True)


@pytest.mark.asyncio
async def test_get_categories(client, seed_products):
    r = await client.get("/api/products/categories")
    assert r.status_code == 200
    assert "electronics" in r.json()


@pytest.mark.asyncio
async def test_get_brands(client, seed_products):
    r = await client.get("/api/products/brands")
    assert r.status_code == 200
    assert "TechCo" in r.json()


@pytest.mark.asyncio
async def test_get_product_by_id(client, seed_products):
    pid = seed_products[0].id
    r = await client.get(f"/api/products/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Смартфон X"


@pytest.mark.asyncio
async def test_get_product_not_found(client):
    r = await client.get("/api/products/99999")
    assert r.status_code == 404
