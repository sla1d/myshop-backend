import pytest


@pytest.mark.asyncio
async def test_validate_promo(client, seed_promo):
    r = await client.post(
        "/api/promos/validate",
        json={"code": "TEST20"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["discount_percent"] == 20
    assert "20%" in data["message"]


@pytest.mark.asyncio
async def test_validate_promo_case_insensitive(client, seed_promo):
    r = await client.post(
        "/api/promos/validate",
        json={"code": "test20"},
    )
    assert r.status_code == 200
    assert r.json()["discount_percent"] == 20


@pytest.mark.asyncio
async def test_validate_promo_not_found(client):
    r = await client.post(
        "/api/promos/validate",
        json={"code": "NOPE"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_validate_promo_inactive(client, session, seed_promo):
    seed_promo.active = False
    await session.commit()
    r = await client.post(
        "/api/promos/validate",
        json={"code": "TEST20"},
    )
    assert r.status_code == 400
    assert "деактивирован" in r.json()["detail"]


@pytest.mark.asyncio
async def test_validate_promo_expired(client, session, seed_promo):
    from datetime import datetime, timezone
    seed_promo.valid_until = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await session.commit()
    r = await client.post(
        "/api/promos/validate",
        json={"code": "TEST20"},
    )
    assert r.status_code == 400
    assert "истёк" in r.json()["detail"]
