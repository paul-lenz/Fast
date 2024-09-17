import os
from dotenv import load_dotenv  # Import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, select
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
# Load environment variables from .env file
load_dotenv()
 
# Retrieve database credentials from environment variables
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD")
# DB_HOST = os.getenv("DB_HOST", "localhost")
DB_HOST = os.getenv("DB_HOST", "dpg-crkesarv2p9s73b6ebm0-a")
# DB_NAME = os.getenv("DB_NAME", "mydatabase")
DB_NAME = os.getenv("DB_NAME", "mydatabase_s5eh")
 
# Construct the async PostgreSQL connection URL
# DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
# DATABASE_URL = f"postgresql://myuser:{DB_PASSWORD}@dpg-crkesarv2p9s73b6ebm0-a/mydatabase_s5eh"
DATABASE_URL = f"postgresql+asyncpg://myuser:OZIzKhmTdB9LwObrMmn6de3arthAHJ36@dpg-crkesarv2p9s73b6ebm0-a/mydatabase_s5eh"
# Initialize async SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()
 
app = FastAPI()
 
# Allow all origins (for development purposes only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow any method (GET, POST, etc.)
    allow_headers=["*"],  # Allow any headers
)
 
Base = declarative_base()
 
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    available = Column(Boolean, default=True)
 
# Create the tables
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
 
# Pydantic models for API input/output
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    available: bool = True
 
    model_config = ConfigDict(from_attributes=True)
 
class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    available: Optional[bool] = None
 
    model_config = ConfigDict(from_attributes=True)
 
# Dependency to get the async session for each request
async def get_db():
    async with SessionLocal() as session:
        yield session
 
@app.get("/")
async def root():
    return {"message": "Service is running"}
 
# GET: Retrieve all items
@app.get("/items", response_model=List[Item])
async def get_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ItemDB))
    items = result.scalars().all()
    return items
 
# GET: Retrieve a single item by ID
@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ItemDB).filter(ItemDB.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
 
# POST: Create a new item
@app.post("/items", response_model=Item)
async def create_item(item: Item, db: AsyncSession = Depends(get_db)):
    db_item = ItemDB(**item.model_dump(exclude_unset=True))
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item
 
@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, updated_item: Item, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ItemDB).filter(ItemDB.id == item_id))
    db_item = result.scalar_one_or_none()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
 
    for key, value in updated_item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    await db.commit()
    await db.refresh(db_item)
    return db_item
 
@app.patch("/items/{item_id}", response_model=Item)
async def patch_item(item_id: int, item_data: ItemUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ItemDB).filter(ItemDB.id == item_id))
    db_item = result.scalar_one_or_none()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
 
    for key, value in item_data.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    await db.commit()
    await db.refresh(db_item)
    return db_item
 
# DELETE: Delete an item by ID
@app.delete("/items/{item_id}")
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ItemDB).filter(ItemDB.id == item_id))
    db_item = result.scalar_one_or_none()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
   
    await db.delete(db_item)
    await db.commit()
    return {"detail": f"Item {item_id} deleted"}