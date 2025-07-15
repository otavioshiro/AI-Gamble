from sqlmodel import SQLModel, create_engine as create_sqlmodel_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./game.db"

# Create an async engine
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async def init_db():
    """
    Initializes the database and creates tables.
    """
    async with async_engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Use this to reset DB
        await conn.run_sync(SQLModel.metadata.create_all)

# Create a configured "Session" class
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    """
    Dependency to get an async database session.
    """
    async with AsyncSessionLocal() as session:
        yield session