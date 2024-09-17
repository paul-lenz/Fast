import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app import app, Base, get_db  # Import your FastAPI app, models, and database dependency

# Test database URL (using an in-memory SQLite database for testing)
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create an AsyncSession for testing
engine = create_async_engine(DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Override the database dependency
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Create the database tables for testing
@pytest.fixture(scope="module")
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Use the test database
@pytest.fixture(scope="module")
async def client(test_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture(autouse=True)
async def clear_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.mark.asyncio
async def test_create_item(client: AsyncClient):
    response = await client.post("/items", json={"name": "Test Item", "price": 10.0})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["price"] == 10.0
    assert "id" in data
    assert isinstance(data["id"], int)

@pytest.mark.asyncio
async def test_get_items(client: AsyncClient):
    await client.post("/items", json={"name": "Test Item", "price": 10.0})
    response = await client.get("/items")
    assert response.status_code == 200
    assert len(response.json()) == 1

@pytest.mark.asyncio
async def test_get_item(client: AsyncClient):
    create_response = await client.post("/items", json={"name": "Test Item", "price": 10.0})
    item_id = create_response.json()["id"]
    response = await client.get(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"

@pytest.mark.asyncio
async def test_update_item(client: AsyncClient):
    create_response = await client.post("/items", json={"name": "Test Item", "price": 10.0})
    item_id = create_response.json()["id"]
    response = await client.put(f"/items/{item_id}", json={"name": "Updated Item", "price": 20.0})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Item"
    assert response.json()["price"] == 20.0

@pytest.mark.asyncio
async def test_patch_item(client: AsyncClient):
    create_response = await client.post("/items", json={"name": "Test Item", "price": 10.0})
    item_id = create_response.json()["id"]
    response = await client.patch(f"/items/{item_id}", json={"name": "Partially Updated Item"})
    assert response.status_code == 200
    assert response.json()["name"] == "Partially Updated Item"
    assert response.json()["price"] == 10.0

@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient):
    create_response = await client.post("/items", json={"name": "Test Item", "price": 10.0})
    item_id = create_response.json()["id"]
    response = await client.delete(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json() == {"detail": f"Item {item_id} deleted"}

@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    response = await client.get("/items/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}