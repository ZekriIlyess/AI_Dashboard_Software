import pytest
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_get_chat_history_unauthorized(client: AsyncClient):
    response = await client.get("/queries/history/session/fake-uuid")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_chat_unauthorized(client: AsyncClient):
    response = await client.post("/queries/chat", json={
        "connection_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "message": "test query"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_chat_requires_valid_connection(client: AsyncClient):
    # Register and login to get token
    await client.post(
        "/auth/register",
        json={"email": "queries@nexus.ai", "password": "testpassword123"}
    )
    login_res = await client.post(
        "/auth/login",
        data={"username": "queries@nexus.ai", "password": "testpassword123"}
    )
    token = login_res.json()["access_token"]
    
    # Try chat with invalid connection
    response = await client.post(
        "/queries/chat", 
        json={
            "connection_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "message": "test query"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    # Should be 404 because connection not found
    assert response.status_code == 404
