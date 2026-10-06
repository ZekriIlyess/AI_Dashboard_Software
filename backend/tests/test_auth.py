import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={"email": "test@nexus.ai", "password": "testpassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["email"] == "test@nexus.ai"

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    # Register first (or rely on the previous test if they run in order, but better to be isolated)
    await client.post(
        "/auth/register",
        json={"email": "login@nexus.ai", "password": "testpassword123"}
    )
    
    response = await client.post(
        "/auth/login",
        data={"username": "login@nexus.ai", "password": "testpassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    response = await client.post(
        "/auth/login",
        data={"username": "login@nexus.ai", "password": "wrongpassword"}
    )
    assert response.status_code == 401
