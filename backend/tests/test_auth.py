import pytest


@pytest.mark.asyncio
async def test_register(client):
    r = await client.post("/register", params={"username": "newuser", "password": "pass123"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_duplicate(client, seed_user):
    r = await client.post("/register", params={"username": "testuser", "password": "pass123"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_register_empty(client):
    r = await client.post("/register", params={"username": "", "password": "pass"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_login(client, seed_user):
    r = await client.post("/login", params={"username": "testuser", "password": "test123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["username"] == "testuser"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_login_wrong_password(client, seed_user):
    r = await client.post("/login", params={"username": "testuser", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent(client):
    r = await client.post("/login", params={"username": "ghost", "password": "pass"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh(client, seed_user):
    from app.core.security import create_refresh_token
    token = create_refresh_token({"sub": str(seed_user.id)})
    r = await client.post("/refresh", json={"refresh_token": token})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_refresh_invalid(client):
    r = await client.post("/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401
